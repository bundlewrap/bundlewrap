# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from abc import ABCMeta
import json
from os.path import exists, join
import re

from bundlewrap.exceptions import BundleError
from bundlewrap.operations import run_local
from bundlewrap.items import BUILTIN_ITEM_ATTRIBUTES, Item
from bundlewrap.items.files import content_processor_jinja2, content_processor_mako
from bundlewrap.utils.dicts import merge_dict, reduce_dict
from bundlewrap.utils.ui import io
from bundlewrap.utils.text import force_text, mark_for_translation as _
from six import add_metaclass
import yaml


NAME_REGEX = r"[a-z0-9-]+/[a-z0-9-]{1,253}"
NAME_REGEX_COMPILED = re.compile(NAME_REGEX)


def log_error(run_result):
    if run_result.return_code != 0:
        io.debug(run_result.stdout.decode('utf-8'))
        io.debug(run_result.stderr.decode('utf-8'))


@add_metaclass(ABCMeta)
class KubernetesItem(Item):
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
    KUBECTL_RESOURCE_TYPE = None
    KUBERNETES_APIVERSION = "v1"

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
            return {'manifest': self.manifest}

    def fix(self, status):
        if status.must_be_deleted:
            result = run_local([
                "kubectl",
                "--context={}".format(self.node.kubectl_context),
                "--namespace={}".format(self.namespace),
                "delete",
                self.KUBECTL_RESOURCE_TYPE,
                self.resource_name,
            ])
            log_error(result)
        else:
            result = run_local([
                "kubectl",
                "--context={}".format(self.node.kubectl_context),
                "--namespace={}".format(self.namespace),
                "apply",
                "-f",
                "-",
            ], data_stdin=self.manifest.encode('utf-8'))
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
    def manifest(self):
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
            user_manifest = yaml.load(content_processor(self))
        elif self.attributes['manifest_file'].endswith(".json"):
            user_manifest = json.loads(content_processor(self))

        return json.dumps(merge_dict(
            {
                'apiVersion': self.KUBERNETES_APIVERSION,
                'kind': self.KIND,
                'metadata': {
                    'name': self.resource_name,
                },
            },
            user_manifest,
        ), indent=4, sort_keys=True)

    @property
    def namespace(self):
        return self.name.split("/", 1)[0]

    def patch_attributes(self, attributes):
        if 'context' not in attributes:
            attributes['context'] = {}
        return attributes

    @property
    def resource_name(self):
        return self.name.split("/", 1)[1]

    def sdict(self):
        result = run_local([
            "kubectl",
            "--context={}".format(self.node.kubectl_context),
            "--namespace={}".format(self.namespace),
            "get",
            "-o",
            "json",
            self.KUBECTL_RESOURCE_TYPE,
            self.resource_name,
        ])
        if result.return_code == 0:
            full_json_response = json.loads(result.stdout)
            if full_json_response.get("status", {}).get("phase") == "Terminating":
                # this resource is currently being deleted, consider it gone
                return None
            return {'manifest': json.dumps(reduce_dict(
                full_json_response,
                json.loads(self.manifest),
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
        if not NAME_REGEX_COMPILED.match(name):
            raise BundleError(_(
                "name for {item_type}:{name} (bundle '{bundle}') "
                "on {node} doesn't match {regex}"
            ).format(
                item_type=cls.ITEM_TYPE_NAME,
                name=name,
                bundle=bundle.name,
                node=bundle.node.name,
                refex=NAME_REGEX,
            ))


class KubernetesClusterRole(KubernetesItem):
    BUNDLE_ATTRIBUTE_NAME = "k8s_clusterroles"
    KIND = "ClusterRole"
    KUBECTL_RESOURCE_TYPE = "clusterroles"
    KUBERNETES_APIVERSION = "rbac.authorization.k8s.io/v1"
    ITEM_TYPE_NAME = "k8s_clusterrole"


class KubernetesClusterRoleBinding(KubernetesItem):
    BUNDLE_ATTRIBUTE_NAME = "k8s_clusterrolebindings"
    KIND = "ClusterRoleBinding"
    KUBECTL_RESOURCE_TYPE = "clusterrolebindings"
    KUBERNETES_APIVERSION = "rbac.authorization.k8s.io/v1"
    ITEM_TYPE_NAME = "k8s_clusterrolebinding"


class KubernetesConfigMap(KubernetesItem):
    BUNDLE_ATTRIBUTE_NAME = "k8s_configmaps"
    KIND = "ConfigMap"
    KUBECTL_RESOURCE_TYPE = "configmaps"
    KUBERNETES_APIVERSION = "v1"
    ITEM_TYPE_NAME = "k8s_configmap"


class KubernetesCronJob(KubernetesItem):
    BUNDLE_ATTRIBUTE_NAME = "k8s_cronjobs"
    KIND = "CronJob"
    KUBECTL_RESOURCE_TYPE = "cronjobs"
    KUBERNETES_APIVERSION = "batch/v1beta1"
    ITEM_TYPE_NAME = "k8s_cronjob"


class KubernetesCustomResourceDefinition(KubernetesItem):
    BUNDLE_ATTRIBUTE_NAME = "k8s_crd"
    KIND = "CustomResourceDefinition"
    KUBECTL_RESOURCE_TYPE = "customresourcedefinition"
    KUBERNETES_APIVERSION = "apiextensions.k8s.io/v1beta1"
    ITEM_TYPE_NAME = "k8s_crd"


class KubernetesDaemonSet(KubernetesItem):
    BUNDLE_ATTRIBUTE_NAME = "k8s_daemonsets"
    KIND = "DaemonSet"
    KUBECTL_RESOURCE_TYPE = "daemonsets"
    KUBERNETES_APIVERSION = "v1"
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
    KUBECTL_RESOURCE_TYPE = "deployments"
    KUBERNETES_APIVERSION = "extensions/v1beta1"
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
    KUBECTL_RESOURCE_TYPE = "ingresses"
    KUBERNETES_APIVERSION = "extensions/v1beta1"
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
    KUBECTL_RESOURCE_TYPE = "namespaces"
    KUBERNETES_APIVERSION = "v1"
    ITEM_TYPE_NAME = "k8s_namespace"

    def get_auto_deps(self, items):
        return []

    @property
    def namespace(self):
        return self.name

    @property
    def resource_name(self):
        return self.name

    @classmethod
    def validate_name(cls, bundle, name):
        pass


class KubernetesPersistentVolumeClain(KubernetesItem):
    BUNDLE_ATTRIBUTE_NAME = "k8s_pvc"
    KIND = "PersistentVolumeClaim"
    KUBECTL_RESOURCE_TYPE = "persistentvolumeclaims"
    KUBERNETES_APIVERSION = "v1"
    ITEM_TYPE_NAME = "k8s_pvc"


class KubernetesSecret(KubernetesItem):
    BUNDLE_ATTRIBUTE_NAME = "k8s_secrets"
    KIND = "Secret"
    KUBECTL_RESOURCE_TYPE = "secrets"
    KUBERNETES_APIVERSION = "v1"
    ITEM_TYPE_NAME = "k8s_secret"

    def get_auto_deps(self, items):
        return super(KubernetesSecret, self).get_auto_deps(items, _secrets=False)


class KubernetesService(KubernetesItem):
    BUNDLE_ATTRIBUTE_NAME = "k8s_services"
    KIND = "Service"
    KUBECTL_RESOURCE_TYPE = "services"
    KUBERNETES_APIVERSION = "v1"
    ITEM_TYPE_NAME = "k8s_service"


class KubernetesServiceAccount(KubernetesItem):
    BUNDLE_ATTRIBUTE_NAME = "k8s_serviceaccounts"
    KIND = "ServiceAccount"
    KUBECTL_RESOURCE_TYPE = "serviceaccounts"
    KUBERNETES_APIVERSION = "v1"
    ITEM_TYPE_NAME = "k8s_serviceaccount"


class KubernetesStatefulSet(KubernetesItem):
    BUNDLE_ATTRIBUTE_NAME = "k8s_statefulsets"
    KIND = "StatefulSet"
    KUBECTL_RESOURCE_TYPE = "statefulsets"
    KUBERNETES_APIVERSION = "apps/v1"
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
