# Kubernetes items

<div class="alert alert-warning">Support for Kubernetes is experimental at this time. Backwards-incompatible changes may happen at any time.</div>

See also: [Guide to Kubernetes](../guide/kubernetes.md)

<br>

Manage resources in Kubernetes clusters.

    k8s_namespaces = {
         "my-app": {},
         "my-previous-app": {'delete': True},
    }

    k8s_deployments = {
        "my-app/my-deployment": {
            'manifest': {
                ...
            },
        },
    }

Note that all item names (except namespaces themselves) must be prefixed with the name of a namespace and a forward slash `/`. Resource items will automatically depend on their namespace if you defined it.

<br>

## Resource types

<table>
<tr><th>Resource type</th><th>Bundle attribute</th><th>apiVersion</th></tr>
<tr><td>Config Map</td><td>k8s_configmaps</td><td>v1</td></tr>
<tr><td>Cron Job</td><td>k8s_cronjobs</td><td>batch/v1beta1</td></tr>
<tr><td>Daemon Set</td><td>k8s_daemonsets</td><td>v1</td></tr>
<tr><td>Deployment</td><td>k8s_deployments</td><td>extensions/v1beta1</td></tr>
<tr><td>Ingress</td><td>k8s_ingresses</td><td>extensions/v1beta1</td></tr>
<tr><td>Namespace</td><td>k8s_namespaces</td><td>v1</td></tr>
<tr><td>Persistent Volume Claim</td><td>k8s_pvc</td><td>v1</td></tr>
<tr><td>Service</td><td>k8s_services</td><td>v1</td></tr>
<tr><td>Secret</td><td>k8s_secrets</td><td>v1</td></tr>
</table>

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
