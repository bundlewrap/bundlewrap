# nodes.py

This file lets you specify or dynamically build a list of nodes in your environment.

All you have to do here is define a Python dictionary called `nodes`. It should look something like this:

	nodes = {
	    "node-1": {
	        'hostname': "node-1.example.com",
	    },
	}



With BundleWrap, the DNS name and the internal identifier for a node ("node-1" in this case) are two separate things.

All fields for a node (including `hostname`) are optional. If you don't give one, BundleWrap will attempt to use the internal identifier to connect to a node:

	nodes = {
	    "node-1.example.com": {},
	}

<br>

# Dynamic node list

You are not confined to the static way of defining a node list as shown above. You can also assemble the `nodes` dictionary dynamically:

	def get_my_nodes_from_ldap():
	    [...]
	    return ldap_nodes

	nodes = get_my_nodes_from_ldap()

<br>

# Node attribute reference

This section is a reference for all possible attributes you can define for a node:

	nodes = {
	    'node-1': {
	        # THIS PART IS EXPLAINED HERE
	    },
	}
<br>

## bundles

A list of [bundle names](bundles.md) to be assigned to this node.

<br>

## hostname

A string used as a DNS name when connecting to this node. May also be an IP address.

<div class="alert">The username and SSH private key for connecting to the node cannot be configured in BundleWrap. If you need to customize those, BundleWrap will honor your <code>~/.ssh/config</code>.</div>


## metadata

This can be a dictionary of arbitrary data. You can access it from your templates as `node.metadata`. Use this to attach custom data (such as a list of IP addresses that should be configured on the target node) to the node. Note that you can also define metadata at the [group level](groups.py.md), but node metadata has higher priority.

<br>

## os

Currently, only the default value of "linux" is supported. Your mileage may vary for "macosx" or "openbsd".

<br>

## use_shadow_passwords

<div class="alert alert-warning">Changing this setting will affect the security of the target system. Only do this for legacy systems that don't support shadow passwords.</div>

This setting will affect how the [user item](../items/user.md) item operates. If set to `False`, password hashes will be written directly to `/etc/passwd` and thus be accessible to any user on the system.
