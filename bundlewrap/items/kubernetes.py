# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from abc import ABCMeta
from json import dumps, loads
import re

from bundlewrap.exceptions import BundleError
from bundlewrap.operations import run_local
from bundlewrap.items import Item
from bundlewrap.utils.dicts import merge_dict, reduce_dict
from bundlewrap.utils.ui import io
from bundlewrap.utils.text import mark_for_translation as _
from six import add_metaclass

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
        'manifest': None,
    }
    KIND = None
    KUBECTL_RESOURCE_TYPE = None
    KUBERNETES_APIVERSION = "v1"

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

    def get_auto_deps(self, items):
        deps = []
        for item in items:
            if item.ITEM_TYPE_NAME == 'k8s_namespace' and item.name == self.namespace:
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
        return deps

    @property
    def manifest(self):
        return dumps(merge_dict(
            {
                'apiVersion': self.KUBERNETES_APIVERSION,
                'kind': self.KIND,
                'metadata': {
                    'name': self.resource_name,
                },
            },
            self.attributes['manifest'] or {},
        ), indent=4, sort_keys=True)

    @property
    def namespace(self):
        return self.name.split("/", 1)[0]

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
            full_json_response = loads(result.stdout)
            if full_json_response.get("status", {}).get("phase") == "Terminating":
                # this resource is currently being deleted, consider it gone
                return None
            return {'manifest': dumps(reduce_dict(
                full_json_response,
                loads(self.manifest),
            ), indent=4, sort_keys=True)}
        elif result.return_code == 1 and "NotFound" in result.stderr.decode('utf-8'):
            return None
        else:
            io.debug(result.stdout.decode('utf-8'))
            io.debug(result.stderr.decode('utf-8'))
            raise RuntimeError(_("error getting state of {}, check `bw --debug`".format(self.id)))

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


class KubernetesDeployment(KubernetesItem):
    BUNDLE_ATTRIBUTE_NAME = "k8s_deployments"
    KIND = "Deployment"
    KUBECTL_RESOURCE_TYPE = "deployments"
    KUBERNETES_APIVERSION = "extensions/v1beta1"
    ITEM_TYPE_NAME = "k8s_deployment"


class KubernetesIngress(KubernetesItem):
    BUNDLE_ATTRIBUTE_NAME = "k8s_ingresses"
    KIND = "Ingress"
    KUBECTL_RESOURCE_TYPE = "ingresses"
    KUBERNETES_APIVERSION = "extensions/v1beta1"
    ITEM_TYPE_NAME = "k8s_ingress"


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


class KubernetesService(KubernetesItem):
    BUNDLE_ATTRIBUTE_NAME = "k8s_services"
    KIND = "Service"
    KUBECTL_RESOURCE_TYPE = "services"
    KUBERNETES_APIVERSION = "v1"
    ITEM_TYPE_NAME = "k8s_service"
