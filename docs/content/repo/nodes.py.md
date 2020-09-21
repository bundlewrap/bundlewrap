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

# One file per node

Especially in larger installations, a single nodes.py can become inconvenient to work with. This example reads nodes from a `nodes/` directory.

	from glob import glob
	from os.path import join

	nodes = {}
	for node in glob(join(repo_path, "nodes", "*.py")):
	    with open(node, 'r') as f:
	        exec(f.read())

Node files would then append `nodes`, like this:

	# nodes/node-1.py
	nodes['node-1'] = {
		'hostname': "node-1.example.com",
	}

Alternatively, consider using [TOML nodes](../guide/toml.md).

<br>

# Node attribute reference

This section is a reference for all possible attributes you can define for a node:

	nodes = {
	    'node-1': {
	        # THIS PART IS EXPLAINED HERE
	    },
	}

All attributes can also be set at the group level, unless noted otherwise.

<br>

## Regular attributes

### bundles

A list of bundle names to be assigned to this node. Bundles set at [group level](groups.py.md) will be added.

<br>

### dummy

Set this to `True` to prevent BundleWrap from creating items for and connecting to this node. This is useful for unmanaged nodes because you can still assign them bundles and metadata like regular nodes and access that from managed nodes (e.g. for monitoring).

<br>

### groups

A list of group names this node should be added to. Be aware that you can also define group members at the group itself and you probably should not use both methods in parallel to avoid confusion.

Cannot be set at group level.

<br>

### hostname

A string used as a DNS name when connecting to this node. May also be an IP address.

<div class="alert alert-info">The username and SSH private key for connecting to the node cannot be configured in BundleWrap. If you need to customize those, BundleWrap will honor your <code>~/.ssh/config</code>.</div>

Cannot be set at group level.

<br>

### metadata

This can be a dictionary of arbitrary data (some type restrictions apply). You can access it from your templates as `node.metadata`. Use this to attach custom data (such as a list of IP addresses that should be configured on the target node) to the node. Note that you can also define metadata at the [group level](groups.py.md#metadata), but node metadata has higher priority.

You are restricted to using only the following types in metadata:

* `dict`
* `list`
* `tuple`
* `set`
* `bool`
* `text` / `unicode`
* `bytes` / `str` (only if decodable into text using UTF-8)
* `int`
* `None`
* `bundlewrap.utils.Fault`

<div class="alert alert-info">Also see the <a href="../groups.py#metadata">documentation for group.metadata</a> and <a href="../metadata.py#Priority">metadata.py</a> for more information.</div>

<br>

### os

Defaults to `"linux"`.

A list of supported OSes can be obtained with `bw debug -n ANY_NODE_NAME -c "print(node.OS_KNOWN)"`.

<br>

### os_version

Set this to your OS version. Note that it must be a tuple of integers, e.g. if you're running Ubuntu 16.04 LTS, it should be `(16, 4)`.

Tuples of integers can be used for easy comparison of versions: `(12, 4) < (16, 4)`

<br>

## OS compatibility overrides

### cmd_wrapper_outer

Used whenever a command needs to be run on a node. Defaults to `"sudo sh -c {}"`. `{}` will be replaced by the quoted command to be run (after `cmd_wrapper_inner` has been applied).

You will need to override this if you're not using `sudo` to gain root privileges (e.g. `doas`) on the node.

<br>

### cmd_wrapper_inner

Used whenever a command needs to be run on a node. Defaults to `"export LANG=C; {}"`. `{}` will be replaced by the command to be run.

You will need to override this if the shell on your node sets environment variables differently.

<br>

### lock_dir

Directory that will be used for creating [locks](../guide/locks.md) on the node. Defaults to `"/var/lib/bundlewrap"`. Will be created if it does not exist.

You will need to override this if `/var/lib` is restricted somehow on your node (SElinux, mounted readonly, etc.).

<br>

### pip_command

This setting will affect how [pkg_pip](../items/pkg_pip.md) will behave. By default, it will use whatever `pip` on your system defaults to.

You will need to override this if you don't have `pip`, but (for example) only `pip3`. Be aware that this setting has no effect when using virtualenvs.

<br>

### use_shadow_passwords

<div class="alert alert-warning">Changing this setting will affect the security of the target system. Only do this for legacy systems that don't support shadow passwords.</div>

This setting will affect how the [user item](../items/user.md) item operates. If set to `False`, password hashes will be written directly to `/etc/passwd` and thus be accessible to any user on the system. If the OS of the node is set to "openbsd", this setting has no effect as `master.shadow` is always used.
