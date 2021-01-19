# API

While most users will interact with BundleWrap through the `bw` command line utility, you can also use it from your own code to extract data or further automate config management tasks.

Even within BundleWrap itself (e.g. templates, libs, and hooks) you are often given repo and/or node objects to work with. Their methods and attributes are documented below.

Some general notes on using BundleWrap's API:

* There can be an arbitrary amount of `bundlewrap.repo.Repository` objects per process.
* Repositories are read as needed and not re-read when something changes. Modifying files in a repo during the lifetime of the matching Repository object may result in undefined behavior.

<br>

## Example

Here's a short example of how to use BundleWrap to get the uptime for a node.

	from bundlewrap.repo import Repository

	repo = Repository("/path/to/my/repo")
	node = repo.get_node("mynode")
	uptime = node.run("uptime")
	print(uptime.stdout)

<br>

## Reference


### bundlewrap.repo.Repository(path)

The starting point of any interaction with BundleWrap. An object of this class represents the repository at the given path. `path` can be a subpath of your repository (e.g., `bundles/nginx/`) and will internally be resolved to the root path of said repository.

<br>

**`.branch`**

The current git branch of this repo. `None` if not in a git repo.

<br>

**`.clean`**

Boolean indicating if there are uncommitted changes in git. `None` if not in a git repo.

<br>

**`.groups`**

A list of all groups in the repo (instances of `bundlewrap.group.Group`)


<br>

**`.nodes`**

A list of all nodes in the repo (instances of `bundlewrap.node.Node`)

<br>

**`.revision`**

The current git, hg or bzr revision of this repo. `None` if no SCM was detected.

<br>

**`.get_group(group_name)`**

Returns the Group object for the given name.

<br>

**`.get_node(node_name)`**

Returns the Node object with the given name.

<br>

**`.nodes_in_all_groups(group_names)`**

Returns a list of Node objects where every node is a member of every group name given.

<br>

**`.nodes_in_any_group(group_names)`**

Returns all Node objects that are a member of at least one of the given group names.

<br>

**`.nodes_in_group(group_name)`**

Returns a list of Node objects in the named group.

<br>

### bundlewrap.node.Node()

A system managed by BundleWrap.

<br>

**`.bundles`**

A list of all bundles associated with this node (instances of `bundlewrap.bundle.Bundle`)

<br>

**`.groups`**

A list of `bundlewrap.group.Group` objects this node belongs to

<br>

**`.hostname`**

The DNS name BundleWrap uses to connect to this node

<br>

**`.items`**

A list of items on this node (instances of subclasses of `bundlewrap.items.Item`)

<br>

**`.magic_number`**

A large number derived from the node's name. This number is very likely to be unique for your entire repository. You can, for example, use this number to easily "jitter" cronjobs:

    '{} {} * * * root /my/script'.format(
        node.magic_number % 60,
        node.magic_number % 2 + 4,
    )

<br>

**`.metadata`**

A dictionary of custom metadata, merged from information in [nodes.py](../repo/nodes.py.md) and [groups.py](../repo/groups.py.md)

<br>

**`.name`**

The internal identifier for this node

<br>

**`.download(remote_path, local_path)`**

Downloads a file from the node.

-   `remote_path` Which file to get from the node
-   `local_path` Where to put the file

<br>

**`.get_item(item_id)`**

Get the Item object with the given ID (e.g. "file:/etc/motd").

<br>

**`.has_bundle(bundle_name)`**

`True` if the node has a bundle with the given name.

<br>

**`.has_any_bundle(bundle_names)`**

`True` if the node has a bundle with any of the given names.

<br>

**`.in_group(group_name)`**

`True` if the node is in a group with the given name.

<br>

**`.in_any_group(group_names)`**

`True` if the node is in a group with any of the given names.

<br>

**`.run(command, may_fail=False)`**

Runs a command on the node. Returns an instance of `bundlewrap.operations.RunResult`.

-   `command` What should be executed on the node
-   `may_fail` If `False`, `bundlewrap.exceptions.RemoteException` will be raised if the command does not return 0.

<br>

**`.upload(local_path, remote_path, mode=None, owner="", group="")`**

Uploads a file to the node.

-   `local_path` Which file to upload
-   `remote_path` Where to put the file on the target node
-   `mode` File mode, e.g. "0644"
-   `owner` Username of the file owner
-   `group` Group name of the file group

<br>

### bundlewrap.group.Group

A user-defined group of nodes.

<br>

**`.name`**

The name of this group

<br>

**`.nodes`**

A list of all nodes in this group (instances of `bundlewrap.node.Node`, includes subgroup members)

<br>

### bundlewrap.utils.Fault

A Fault acts as a lazy stand-in object for the result of a given callback function. These objects are returned from the "vault" attached to `Repository` objects:

	>>> repo.vault.password_for("demo")
	<bundlewrap.utils.Fault object at 0x10782b208>

Only when the `value` property of a Fault is accessed or when the Fault is converted to a string, the callback function is executed. In the example above, this means that the password is only generated when it is really required (e.g. when used in a template). This is particularly useful when used in metadata in connection with [secrets](secrets.md). Users will be able to generate metadata with Faults in it, even if they lack the required keys for the decryption operation represented by the Fault. The key will only be required for files etc. that actually use it. If a Fault cannot be resolved (e.g. for lack of the required key), BundleWrap can just skip the item using the Fault, while still allowing other items on the same node to be applied.

Faults also support some rudimentary string operations such as appending a string or another Fault, as well as some string methods:

	>>> f = repo.vault.password_for("1") + ":" + repo.vault.password_for("2")
	>>> f
	<bundlewrap.utils.Fault object at 0x10782b208>
	>>> f.value
	'VOd5PC:JUgYUb'
	>>> f += " "
	>>> f.value
	'VOd5PC:JUgYUb '
	>>> f.strip().value
	'VOd5PC:JUgYUb'
	>>> repo.vault.password_for("1").format_into("Password: {}").value
	'Password: VOd5PC'
	>>> repo.vault.password_for("1").b64encode().value
	'Vk9kNVA='
	>>> repo.vault.password_for("1").as_htpasswd_entry("username").value
	'username:$apr1$8be694c7…'

These string methods are supported on Faults: `format`, `lower`, `lstrip`, `replace`, `rstrip`, `strip`, `upper`, `zfill`
