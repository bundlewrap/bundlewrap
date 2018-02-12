# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from abc import ABCMeta
from json import dumps, loads

from bundlewrap.exceptions import BundleError
from bundlewrap.operations import run_local
from bundlewrap.items import Item
from bundlewrap.utils.dicts import (
    map_dict_keys,
    merge_dict,
    reduce_dict,
    set_value_at_key_path,
    value_at_key_path,
)
from bundlewrap.utils.ui import io
from bundlewrap.utils.text import mark_for_translation as _
from six import add_metaclass


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
            # TODO handle errors
            #io.stdout(result.stdout.decode('utf-8'))
            #io.stdout(result.stderr.decode('utf-8'))
        else:
            result = run_local([
                "kubectl",
                "--context={}".format(self.node.kubectl_context),
                "--namespace={}".format(self.namespace),
                "apply",
                #"--validate=false",
                #"--openapi-validation=false",
                "-f",
                "-",
            ], data_stdin=self.manifest.encode('utf-8'))
            # TODO handle errors
            #io.stdout(result.stdout.decode('utf-8'))
            #io.stdout(result.stderr.decode('utf-8'))

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
        return self.name.split("/")[0]

    @property
    def resource_name(self):
        return self.name.split("/")[1]

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
            return {'manifest': dumps(reduce_dict(full_json_response, loads(self.manifest)), indent=4, sort_keys=True)}
        elif result.return_code == 1 and "NotFound" in result.stderr.decode('utf-8'):
            return None
        else:
            # TODO handle errors
            #io.stdout(result.stdout.decode('utf-8'))
            #io.stdout(result.stderr.decode('utf-8'))
            assert False


class KubernetesDeployment(KubernetesItem):
    BUNDLE_ATTRIBUTE_NAME = "k8s_deployments"
    KIND = "Deployment"
    KUBECTL_RESOURCE_TYPE = "deployments"
    KUBERNETES_APIVERSION = "extensions/v1beta1"
    ITEM_TYPE_NAME = "k8s_deployment"


class KubernetesNamespace(KubernetesItem):
    BUNDLE_ATTRIBUTE_NAME = "k8s_namespaces"
    KIND = "Namespace"
    KUBECTL_RESOURCE_TYPE = "namespaces"
    KUBERNETES_APIVERSION = "v1"
    ITEM_TYPE_NAME = "k8s_namespace"

    @property
    def namespace(self):
        return self.name

    @property
    def resource_name(self):
        return self.name
