# Kubernetes

<div class="alert alert-warning">Support for Kubernetes is experimental at this time. Backwards-incompatible changes may happen at any time.</div>

To manage a Kubernetes cluster with BundleWrap, you first need to set up a kubectl context that works with the cluster. If you're running on Google Kubernetes Engine for example, this can be accomplished with:

	gcloud auth login
	gcloud container clusters get-credentials your-cluster --zone your-zone --project your-project

You also need to make sure context names are the same on your teammates' machines.

<br>

## Setting up a node

Each Kubernetes cluster you manage becomes a node. Here is an example `nodes.py`:

	nodes = {
	     "my-cluster": {
	         'os': 'kubernetes',
	         'bundles': ["my-app"],
	         'kubectl_context': "my-context",
	     },
	}

<br>

## Kubernetes bundles

You can then proceed to write bundles as with regular nodes, but using the [k8s_ items](../items/k8s.md):

    k8s_namespaces = {
         "my-app": {},
    }

    k8s_deployments = {
        "my-app/my-deployment": {
            'manifest': {
                "spec": {
                    "selector": {
                        "matchLabels": {
                            "app": "nginx",
                        },
                    },
                    "replicas": 2,
                    "template": {
                        "metadata": {
                            "labels": {
                                "app": "nginx",
                            },
                        },
                        "spec": {
                            "containers": [
                                {
                                    "name": "nginx",
                                    "image": "nginx:latest",
                                    "ports": [
                                        {"containerPort": 80},
                                    ]
                                },
                            ],
                        },
                    },
                },
            },
        },
    }

All item names (except namespaces themselves) must be prefixed with the name of a namespace and a forward slash `/`. Note that BundleWrap will include defaults for the `Kind` and `metadata/name` keys, but you can override them if you must.

Alternatively, you can keep your resource definitions in manifest files:

    k8s_namespaces = {
         "my-app": {},
    }

    k8s_deployments = {
        "my-app/my-deployment": {
            'manifest_file': "my_deployment.yaml",
        },
    }

BundleWrap will then look for `my_deployment.yaml` in `bundles/<bundle>/manifests/`. You can also use [templating](../items/k8s.md#manifest_processor) in these files.
