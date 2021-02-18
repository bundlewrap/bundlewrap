from abc import ABCMeta
import json
from os.path import exists, join
import re

from bundlewrap.exceptions import BundleError
from bundlewrap.metadata import metadata_to_json
from bundlewrap.items import BUILTIN_ITEM_ATTRIBUTES, Item
from bundlewrap.items.files import content_processor_jinja2, content_processor_mako
from bundlewrap.utils.dicts import diff_value_text, merge_dict, reduce_dict
from bundlewrap.utils.ui import io
from bundlewrap.utils.text import force_text, mark_for_translation as _
import yaml


def log_error(run_result):
    if run_result.return_code != 0:
        io.debug(run_result.stdout.decode('utf-8'))
        io.debug(run_result.stderr.decode('utf-8'))


class KubernetesItem(Item, metaclass=ABCMeta):
    """
    A generic Kubernetes item.
    """
    ITEM_ATTRIBUTES = {
        'delete': False,
        'encoding': "utf-8",  # required by content processors
        'manifest': None,
        'manifest_file': None,
        'manifest_processor': None,
        'context': None,
    }
    KIND = None
    NAME_REGEX = r"^[a-z0-9-\.]{1,253}/[a-z0-9-\.]{1,253}$"
    NAME_REGEX_COMPILED = re.compile(NAME_REGEX)

    def __init__(self, *args, **kwargs):
        super(KubernetesItem, self).__init__(*args, **kwargs)
        self.item_data_dir = join(self.bundle.bundle_data_dir, "manifests")
        self.item_dir = join(self.bundle.bundle_dir, "manifests")

    @property
    def _template_content(self):  # required by content processors
        filename = join(self.item_data_dir, self.attributes['manifest_file'])
        if not exists(filename):
            filename = join(self.item_dir, self.attributes['manifest_file'])
        with open(filename, 'rb') as f:
            return force_text(f.read())

    def cdict(self):
        if self.attributes['delete']:
            return None
        else:
            return {'manifest': json.dumps(
                self.nuke_k8s_status(json.loads(self.manifest)),
                indent=4, sort_keys=True,
            )}

    def display_on_create(self, cdict):
        cdict['manifest'] = diff_value_text("", "", force_text(cdict['manifest'])).rstrip("\n")
        return cdict

    def display_on_delete(self, sdict):
        sdict['manifest'] = diff_value_text("", force_text(sdict['manifest']), "").rstrip("\n")
        return sdict

    def fix(self, status):
        if status.must_be_deleted:
            result = self.run_local(self._kubectl + ["delete", self.KIND, self.resource_name])
            log_error(result)
        else:
            result = self.run_local(
                self._kubectl + ["apply", "-f", "-"],
                data_stdin=self.manifest.encode('utf-8'),
            )
            log_error(result)

    def get_auto_deps(self, items, _secrets=True):
        deps = []
        for item in items:
            if (
                item.ITEM_TYPE_NAME == 'k8s_namespace' and
                item.name == self.namespace
            ):
                if item.attributes['delete'] and not self.attributes['delete']:
                    raise BundleError(_(
                        "{item} (bundle '{bundle}' on {node}) "
                        "cannot exist in namespace marked for deletion"
                    ).format(
                        item=self.id,
                        bundle=self.bundle.name,
                        node=self.node.name,
                    ))
                deps.append(item.id)
            elif (
                _secrets and
                item.ITEM_TYPE_NAME == 'k8s_secret' and
                item.namespace == self.namespace
            ):
                deps.append(item.id)
        return deps

    @property
    def _kubectl(self):
        cmdline = [
            "kubectl",
            "--context={}".format(self.node.kubectl_context),
        ]
        if self.namespace:
            cmdline.append("--namespace={}".format(self.namespace))
        return cmdline

    @property
    def _manifest_dict(self):
        if self.attributes['manifest_processor'] == 'jinja2':
            content_processor = content_processor_jinja2
        elif self.attributes['manifest_processor'] == 'mako':
            content_processor = content_processor_mako
        else:
            content_processor = lambda item: item._template_content.encode('utf-8')

        if self.attributes['manifest'] is not None or self.attributes['manifest_file'] is None:
            user_manifest = self.attributes['manifest'] or {}
        elif (
            self.attributes['manifest_file'].endswith(".yaml") or
            self.attributes['manifest_file'].endswith(".yml")
        ):
            user_manifest = yaml.load(content_processor(self), Loader=yaml.SafeLoader)
        elif self.attributes['manifest_file'].endswith(".json"):
            user_manifest = json.loads(content_processor(self))

        merged_manifest = merge_dict(
            {
                'kind': self.KIND,
                'metadata': {
                    'name': self.name.split("/")[-1],
                },
            },
            user_manifest,
        )

        if merged_manifest.get('apiVersion') is None:
            raise BundleError(_(
                "{item} from bundle '{bundle}' needs an apiVersion in its manifest"
            ).format(item=self.id, bundle=self.bundle.name))

        return merged_manifest

    @property
    def manifest(self):
        return metadata_to_json(self._manifest_dict)

    @property
    def namespace(self):
        return self.name.split("/", 1)[0] or None

    def nuke_k8s_status(self, manifest):
        if 'status' in manifest:
            del manifest['status']
        return manifest

    def patch_attributes(self, attributes):
        if 'context' not in attributes:
            attributes['context'] = {}
        return attributes

    def preview(self):
        if self.attributes['delete'] is True:
            raise ValueError
        return yaml.dump(json.loads(self.manifest), default_flow_style=False)

    @property
    def resource_name(self):
        return self._manifest_dict['metadata']['name']

    def sdict(self):
        result = self.run_local(self._kubectl + ["get", "-o", "json", self.KIND, self.resource_name])
        if result.return_code == 0:
            full_json_response = json.loads(result.stdout.decode('utf-8'))
            if full_json_response.get("status", {}).get("phase") == "Terminating":
                # this resource is currently being deleted, consider it gone
                return None
            return {'manifest': json.dumps(reduce_dict(
                full_json_response,
                self.nuke_k8s_status(json.loads(self.manifest)),
            ), indent=4, sort_keys=True)}
        elif result.return_code == 1 and "NotFound" in result.stderr.decode('utf-8'):
            return None
        else:
            io.debug(result.stdout.decode('utf-8'))
            io.debug(result.stderr.decode('utf-8'))
            raise RuntimeError(_("error getting state of {}, check `bw --debug`".format(self.id)))

    @classmethod
    def validate_attributes(cls, bundle, item_id, attributes):
        if attributes.get('delete', False):
            for attr in attributes.keys():
                if attr not in ['delete'] + list(BUILTIN_ITEM_ATTRIBUTES.keys()):
                    raise BundleError(_(
                        "{item} from bundle '{bundle}' cannot have other "
                        "attributes besides 'delete'"
                    ).format(item=item_id, bundle=bundle.name))
        if attributes.get('manifest') and attributes.get('manifest_file'):
            raise BundleError(_(
                "{item} from bundle '{bundle}' cannot have both 'manifest' and 'manifest_file'"
            ).format(item=item_id, bundle=bundle.name))
        if attributes.get('manifest_processor') not in (None, 'jinja2', 'mako'):
            raise BundleError(_(
                "{item} from bundle '{bundle}' has invalid manifest_processor "
                "(must be 'jinja2' or 'mako')"
            ).format(item=item_id, bundle=bundle.name))

    @classmethod
    def validate_name(cls, bundle, name):
        if not cls.NAME_REGEX_COMPILED.match(name):
            raise BundleError(_(
                "name for {item_type}:{name} (bundle '{bundle}') "
                "on {node} doesn't match {regex}"
            ).format(
                item_type=cls.ITEM_TYPE_NAME,
                name=name,
                bundle=bundle.name,
                node=bundle.node.name,
                regex=cls.NAME_REGEX,
            ))


class KubernetesRawItem(KubernetesItem):
    BUNDLE_ATTRIBUTE_NAME = "k8s_raw"
    ITEM_TYPE_NAME = "k8s_raw"
    NAME_REGEX = r"^([a-z0-9-\.]{1,253})?/[a-zA-Z0-9-\.]{1,253}/[a-z0-9-\.]{1,253}$"
    NAME_REGEX_COMPILED = re.compile(NAME_REGEX)

    def _check_bundle_collisions(self, items):
        super(KubernetesRawItem, self)._check_bundle_collisions(items)
        for item in items:
            if item == self or not isinstance(item, KubernetesItem):
                continue
            if item.KIND == self.KIND and item.resource_name == self.resource_name:
                raise BundleError(_(
                    "duplicate definition of {item} (from bundle {bundle}) "
                    "as {item2} (from bundle {bundle2}) on {node}"
                ).format(
                    item=self.id,
                    bundle=self.bundle.name,
                    item2=item.id,
                    bundle2=item.bundle.name,
                    node=self.node.name,
                ))

    def get_auto_deps(self, items):
        deps = super(KubernetesRawItem, self).get_auto_deps(items)
        for item in items:
            if (
                item.ITEM_TYPE_NAME == 'k8s_crd' and
                item._manifest_dict.get('spec', {}).get('names', {}).get('kind') == self.KIND
            ):
                deps.append(item.id)
        return deps

    @property
    def KIND(self):
        return self.name.split("/", 2)[1]


class KubernetesClusterRole(KubernetesItem):
    BUNDLE_ATTRIBUTE_NAME = "k8s_clusterroles"
    KIND = "ClusterRole"
    ITEM_TYPE_NAME = "k8s_clusterrole"
    NAME_REGEX = r"^[a-z0-9-\.]{1,253}$"
    NAME_REGEX_COMPILED = re.compile(NAME_REGEX)

    @property
    def namespace(self):
        return None


class KubernetesClusterRoleBinding(KubernetesItem):
    BUNDLE_ATTRIBUTE_NAME = "k8s_clusterrolebindings"
    KIND = "ClusterRoleBinding"
    ITEM_TYPE_NAME = "k8s_clusterrolebinding"
    NAME_REGEX = r"^[a-z0-9-\.]{1,253}$"
    NAME_REGEX_COMPILED = re.compile(NAME_REGEX)

    def get_auto_deps(self, items):
        deps = super(KubernetesClusterRoleBinding, self).get_auto_deps(items)
        deps.append("k8s_clusterrole:")
        return deps

    @property
    def namespace(self):
        return None


class KubernetesConfigMap(KubernetesItem):
    BUNDLE_ATTRIBUTE_NAME = "k8s_configmaps"
    KIND = "ConfigMap"
    ITEM_TYPE_NAME = "k8s_configmap"


class KubernetesCronJob(KubernetesItem):
    BUNDLE_ATTRIBUTE_NAME = "k8s_cronjobs"
    KIND = "CronJob"
    ITEM_TYPE_NAME = "k8s_cronjob"


class KubernetesCustomResourceDefinition(KubernetesItem):
    BUNDLE_ATTRIBUTE_NAME = "k8s_crd"
    KIND = "CustomResourceDefinition"
    ITEM_TYPE_NAME = "k8s_crd"
    NAME_REGEX = r"^[a-z0-9-\.]{1,253}$"
    NAME_REGEX_COMPILED = re.compile(NAME_REGEX)

    def get_auto_deps(self, items):
        return []

    @property
    def namespace(self):
        return None


class KubernetesDaemonSet(KubernetesItem):
    BUNDLE_ATTRIBUTE_NAME = "k8s_daemonsets"
    KIND = "DaemonSet"
    ITEM_TYPE_NAME = "k8s_daemonset"

    def get_auto_deps(self, items):
        deps = super(KubernetesDaemonSet, self).get_auto_deps(items)
        for item in items:
            if (
                item.ITEM_TYPE_NAME in ('k8s_pvc', 'k8s_configmap') and
                item.namespace == self.namespace
            ):
                deps.append(item.id)
        return deps


class KubernetesDeployment(KubernetesItem):
    BUNDLE_ATTRIBUTE_NAME = "k8s_deployments"
    KIND = "Deployment"
    ITEM_TYPE_NAME = "k8s_deployment"

    def get_auto_deps(self, items):
        deps = super(KubernetesDeployment, self).get_auto_deps(items)
        for item in items:
            if (
                item.ITEM_TYPE_NAME in ('k8s_pvc', 'k8s_configmap') and
                item.namespace == self.namespace
            ):
                deps.append(item.id)
        return deps


class KubernetesIngress(KubernetesItem):
    BUNDLE_ATTRIBUTE_NAME = "k8s_ingresses"
    KIND = "Ingress"
    ITEM_TYPE_NAME = "k8s_ingress"

    def get_auto_deps(self, items):
        deps = super(KubernetesIngress, self).get_auto_deps(items)
        for item in items:
            if (
                item.ITEM_TYPE_NAME == 'k8s_service' and
                item.namespace == self.namespace
            ):
                deps.append(item.id)
        return deps


class KubernetesNamespace(KubernetesItem):
    BUNDLE_ATTRIBUTE_NAME = "k8s_namespaces"
    KIND = "Namespace"
    ITEM_TYPE_NAME = "k8s_namespace"
    NAME_REGEX = r"^[a-z0-9-\.]{1,253}$"
    NAME_REGEX_COMPILED = re.compile(NAME_REGEX)

    def get_auto_deps(self, items):
        return []


class KubernetesNetworkPolicy(KubernetesItem):
    BUNDLE_ATTRIBUTE_NAME = "k8s_networkpolicies"
    KIND = "NetworkPolicy"
    ITEM_TYPE_NAME = "k8s_networkpolicy"
    NAME_REGEX = r"^([a-z0-9-\.]{1,253})?/[a-z0-9-\.]{1,253}$"
    NAME_REGEX_COMPILED = re.compile(NAME_REGEX)


class KubernetesPersistentVolumeClain(KubernetesItem):
    BUNDLE_ATTRIBUTE_NAME = "k8s_pvc"
    KIND = "PersistentVolumeClaim"
    ITEM_TYPE_NAME = "k8s_pvc"


class KubernetesRole(KubernetesItem):
    BUNDLE_ATTRIBUTE_NAME = "k8s_roles"
    KIND = "Role"
    ITEM_TYPE_NAME = "k8s_role"


class KubernetesRoleBinding(KubernetesItem):
    BUNDLE_ATTRIBUTE_NAME = "k8s_rolebindings"
    KIND = "RoleBinding"
    ITEM_TYPE_NAME = "k8s_rolebinding"

    def get_auto_deps(self, items):
        deps = super(KubernetesRoleBinding, self).get_auto_deps(items)
        deps.append("k8s_role:")
        return deps


class KubernetesSecret(KubernetesItem):
    BUNDLE_ATTRIBUTE_NAME = "k8s_secrets"
    KIND = "Secret"
    ITEM_TYPE_NAME = "k8s_secret"

    def get_auto_deps(self, items):
        return super(KubernetesSecret, self).get_auto_deps(items, _secrets=False)


class KubernetesService(KubernetesItem):
    BUNDLE_ATTRIBUTE_NAME = "k8s_services"
    KIND = "Service"
    ITEM_TYPE_NAME = "k8s_service"


class KubernetesServiceAccount(KubernetesItem):
    BUNDLE_ATTRIBUTE_NAME = "k8s_serviceaccounts"
    KIND = "ServiceAccount"
    ITEM_TYPE_NAME = "k8s_serviceaccount"


class KubernetesStatefulSet(KubernetesItem):
    BUNDLE_ATTRIBUTE_NAME = "k8s_statefulsets"
    KIND = "StatefulSet"
    ITEM_TYPE_NAME = "k8s_statefulset"

    def get_auto_deps(self, items):
        deps = super(KubernetesStatefulSet, self).get_auto_deps(items)
        for item in items:
            if (
                item.ITEM_TYPE_NAME in ('k8s_pvc', 'k8s_configmap') and
                item.namespace == self.namespace
            ):
                deps.append(item.id)
        return deps
