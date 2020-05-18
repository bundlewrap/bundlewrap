# Kubernetes items

<div class="alert alert-warning">Support for Kubernetes is experimental at this time. Backwards-incompatible changes may happen at any time.</div>

See also: [Guide to Kubernetes](../guide/kubernetes.md)

<br>

Manage resources in Kubernetes clusters.

    k8s_namespaces = {
         "my-app": {
            'manifest': {
                'apiVersion': "v1",
            },
         },
         "my-previous-app": {'delete': True},
    }

    k8s_deployments = {
        "my-app/my-deployment": {
            'manifest': {
                ...
            },
        },
    }

Note that the names of all items in a namespace must be prefixed with the name of their namespace and a forward slash `/`. Resource items will automatically depend on their namespace if you defined it.

<br>

## Resource types

<table>
<tr><th>Resource type</th><th>Bundle attribute</th></tr>
<tr><td>Cluster Role</td><td>k8s_clusterroles</td></tr>
<tr><td>Cluster Role Binding</td><td>k8s_clusterrolebindings</td></tr>
<tr><td>Config Map</td><td>k8s_configmaps</td></tr>
<tr><td>Cron Job</td><td>k8s_cronjobs</td></tr>
<tr><td>Custom Resource Definition</td><td>k8s_crd</td></tr>
<tr><td>Daemon Set</td><td>k8s_daemonsets</td></tr>
<tr><td>Deployment</td><td>k8s_deployments</td></tr>
<tr><td>Ingress</td><td>k8s_ingresses</td></tr>
<tr><td>Namespace</td><td>k8s_namespaces</td></tr>
<tr><td>Network Policy</td><td>k8s_networkpolicies</td></tr>
<tr><td>Persistent Volume Claim</td><td>k8s_pvc</td></tr>
<tr><td>Role</td><td>k8s_roles</td></tr>
<tr><td>Role Binding</td><td>k8s_rolebindings</td></tr>
<tr><td>Service</td><td>k8s_services</td></tr>
<tr><td>Service Account</td><td>k8s_serviceaccounts</td></tr>
<tr><td>Secret</td><td>k8s_secrets</td></tr>
<tr><td>StatefulSet</td><td>k8s_statefulsets</td></tr>
<tr><td>(any)</td><td>k8s_raw</td></tr>
</table>

You can define [Custom Resources](https://kubernetes.io/docs/concepts/api-extension/custom-resources/) like this:

    k8s_crd = {
        "custom-thing": {
            'manifest': {
                'apiVersion': "apiextensions.k8s.io/v1beta1",
                'spec': {
                    'names': {
                        'kind': "CustomThing",
                    },
                },
            },
        },
    }

    k8s_raw = {
        "foo/CustomThing/baz": {
            'manifest': {
                'apiVersion': "example.com/v1",
            },
        },
    }

The special `k8s_raw` items can also be used to create resources that BundleWrap does not support natively:

    k8s_raw = {
        "foo/HorizontalPodAutoscaler/baz": {
            'manifest': {
                'apiVersion': "autoscaling/v2beta1",
            },
        },
    }

Resources outside any namespace can be created with `k8s_raw` by omitting the namespace in the item name (so that the name starts with `/`).

<br>

# Attribute reference

See also: [The list of generic builtin item attributes](../repo/items.py.md#builtin-item-attributes)

<hr>

## context

Only used with Mako and Jinja2 manifests (see `manifest_processing` below). The values of this dictionary will be available from within the template as variables named after the respective keys.

<hr>

## delete

Set this to `True` to have the resource removed.

<hr>

## manifest

The resource definition (as defined in the [Kubernetes API](https://kubernetes.io/docs/reference/)) formatted as a Python dictionary (will be converted to JSON and passed to `kubectl apply`). Mutually exclusive with `manifest_file`.

<hr>

## manifest_file

Filename of the resource definition relative to the `manifests` subdirectory of your bundle. Filenames must end in `.yaml`, `.yml`, or `.json` to indicate file format. Mutually exclusive with `manifest`.

<br>

## manifest_processor

Set this to `jinja2` or `mako` if you want to use a template engine to process your `manifest_file`. Defaults to `None`.
