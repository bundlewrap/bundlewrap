# Kubernetes items

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

## delete

Set this to `True` to have the resource removed.

<hr>

## manifest

The resource definition (as defined in the [Kubernetes API](https://kubernetes.io/docs/reference/)) formatted as a Python dictionary (will be converted to JSON and passed to `kubectl apply`).
