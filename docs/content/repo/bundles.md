<h1>Bundles</h1>

Bundles are subdirectories of the `bundles/` directory of your BundleWrap repository.

# items.py

Within each bundle, there may be a file called `items.py`. It defines any number of magic attributes that are automatically processed by BundleWrap. Each attribute is a dictionary mapping an item name (such as a file name) to a dictionary of attributes (e.g. file ownership information).

A typical bundle might look like this:

	files = {
	    '/etc/hosts': {
	         'owner': "root",
	         'group': "root",
	         'mode': "0664",
	         [...]
	    },
	}

	users = {
	    'janedoe': {
	        'home': "/home/janedoe",
	        'shell': "/bin/zsh",
	        [...]
	    },
	    'johndoe': {
	        'home': "/home/johndoe",
	        'shell': "/bin/bash",
	        [...]
	    },
	}

This bundle defines the attributes `files` and `users`. Within the `users` attribute, there are two `user` items. Each item maps its name to a dictionary that is understood by the specific kind of item. Below you will find a reference of all builtin item types and the attributes they understand. You can also [define your own item types](../guide/dev_item.md).

<br>

## Item types

This table lists all item types included in BundleWrap along with the bundle attributes they understand.

<table>
<tr><th>Type</th><th>Bundle attribute</th><th>Description</th></tr>
<tr><td><a href="../../items/action">action</a></td><td><code>actions</code></td><td>Actions allow you to run commands on every <code>bw apply</code></td></tr>
<tr><td><a href="../../items/directory">directory</a></td><td><code>directories</code></td><td>Manages permissions and ownership for directories</td></tr>
<tr><td><a href="../../items/file">file</a></td><td><code>files</code></td><td>Manages contents, permissions, and ownership for files</td></tr>
<tr><td><a href="../../items/group">group</a></td><td><code>groups</code></td><td>Manages groups by wrapping <code>groupadd</code>, <code>groupmod</code> and <code>groupdel</code></td></tr>
<tr><td><a href="../../items/pkg_apt">pkg_apt</a></td><td><code>pkg_apt</code></td><td>Installs and removes packages with APT</td></tr>
<tr><td><a href="../../items/pkg_dnf">pkg_dnf</a></td><td><code>pkg_dnf</code></td><td>Installs and removes packages with dnf</td></tr>
<tr><td><a href="../../items/pkg_pacman">pkg_pacman</a></td><td><code>pkg_pacman</code></td><td>Installs and removes packages with pacman</td></tr>
<tr><td><a href="../../items/pkg_pip">pkg_pip</a></td><td><code>pkg_pip</code></td><td>Installs and removes Python packages with pip</td></tr>
<tr><td><a href="../../items/pkg_snap">pkg_snap</a></td><td><code>pkg_snap</code></td><td>Installs and removes packages with snap</td></tr>
<tr><td><a href="../../items/pkg_yum">pkg_yum</a></td><td><code>pkg_yum</code></td><td>Installs and removes packages with yum</td></tr>
<tr><td><a href="../../items/pkg_zypper">pkg_zypper</a></td><td><code>pkg_zypper</code></td><td>Installs and removes packages with zypper</td></tr>
<tr><td><a href="../../items/postgres_db">postgres_db</a></td><td><code>postgres_dbs</code></td><td>Manages Postgres databases</td></tr>
<tr><td><a href="../../items/postgres_role">postgres_role</a></td><td><code>postgres_roles</code></td><td>Manages Postgres roles</td></tr>
<tr><td><a href="../../items/pkg_pip">pkg_pip</a></td><td><code>pkg_pip</code></td><td>Installs and removes Python packages with pip</td></tr>
<tr><td><a href="../../items/pkg_openbsd">pkg_openbsd</a></td><td><code>pkg_openbsd</code></td><td>Installs and removes OpenBSD packages with pkg_add/pkg_delete</td></tr>
<tr><td><a href="../../items/svc_openbsd">svc_openbsd</a></td><td><code>svc_openbsd</code></td><td>Starts and stops services with OpenBSD's rc</td></tr>
<tr><td><a href="../../items/svc_systemd">svc_systemd</a></td><td><code>svc_systemd</code></td><td>Starts and stops services with systemd</td></tr>
<tr><td><a href="../../items/svc_systemv">svc_systemv</a></td><td><code>svc_systemv</code></td><td>Starts and stops services with traditional System V init scripts</td></tr>
<tr><td><a href="../../items/svc_upstart">svc_upstart</a></td><td><code>svc_upstart</code></td><td>Starts and stops services with Upstart</td></tr>
<tr><td><a href="../../items/symlink">symlink</a></td><td><code>symlinks</code></td><td>Manages symbolic links and their ownership</td></tr>
<tr><td><a href="../../items/user">user</a></td><td><code>users</code></td><td>Manages users by wrapping <code>useradd</code>, <code>usermod</code> and <code>userdel</code></td></tr>
</table>

<br>

## Builtin item attributes

There are also attributes that can be applied to any kind of item.

<br>

### comment

This is a string that will be displayed in interactive mode (`bw apply -i`) whenever the item is to be changed in any way. You can use it to warn users before they start disruptive actions.

<br>

### error_on_missing_fault

This will simply skip an item instead of raising an error when a Fault used for an attribute on the item is unavailable. Faults are special objects used by `repo.vault` to [handle secrets](../guide/secrets.md). A Fault being unavailable can mean you're missing the secret key required to decrypt a secret you're trying to use as an item attribute value.

Defaults to `False`.

<br>

### needs

One such attribute is `needs`. It allows for setting up dependencies between items. This is not something you will have to to very often, because there are already implicit dependencies between items types (e.g. all files depend on the users owning them). Here are two examples:

	my_items = {
	    'item1': {
	        [...]
	        'needs': [
	            'file:/etc/foo.conf',
	        ],
	    },
	    'item2': {
	        ...
	        'needs': [
	            'pkg_apt:',
	            'bundle:foo',
	        ],
	    }
	}

The first item (`item1`, specific attributes have been omitted) depends on a file called `/etc/foo.conf`, while `item2` depends on all APT packages being installed and every item in the foo bundle.

<br>

### needed_by

This attribute is an alternative way of defining dependencies. It works just like `needs`, but in the other direction. There are only three scenarios where you should use `needed_by` over `needs`:

* if you need all items of a certain type to depend on something or
* if you need all items in a bundle to depend on something or
* if you need an item in a bundle you can't edit (e.g. because it's provided by a community-maintained [plugin](plugins.md)) to depend on something in your bundles

<br>

### tags

A list of strings to tag an item with. Tagging has no immediate effect in itself, but can be useful in a number of places. For example, you can add dependencies on all items with a given tag:

    pkg_apt = {
        "mysql-server-{}".format(node.metadata.get('mysql_version', "5.5")): {
            'tags': ["provides-mysqld"],
        },
    }

    svc_systemd = {
        "myapp": {
            'needs': ["tag:provides-mysqld"],
        },
    }

In this simplified example we save ourselves from duplicating the logic that gets the current MySQL version from metadata (which is probably overkill here, but you might encounter more complex situations).

<br>

### triggers and triggered

In some scenarios, you may want to execute an [action](../items/action.md) only when an item is fixed (e.g. restart a daemon after a config file has changed or run `postmap` after updating an alias file). To do this, BundleWrap has the builtin atttribute `triggers`. You can use it to point to any item that has its `triggered` attribute set to `True`. Such items will only be checked (or in the case of actions: run) if the triggering item is fixed (or a triggering action completes successfully).

	files = {
	    '/etc/daemon.conf': {
	        [...]
	        'triggers': [
	            'action:restart_daemon',
	        ],
	    },
	}

	actions = {
	    'restart_daemon': {
	    	'command': "service daemon restart",
	    	'triggered': True,
	    },
	}

The above example will run `service daemon restart` every time BundleWrap successfully applies a change to `/etc/daemon.conf`. If an action is triggered multiple times, it will only be run once.

Similar to `needed_by`, `triggered_by` can be used to define a `triggers` relationship from the opposite direction.

<br>

### preceded_by

Operates like `triggers`, but will apply the triggered item *before* the triggering item. Let's look at an example:

	files = {
	    '/etc/example.conf': {
	        [...]
	        'preceded_by': [
	            'action:backup_example',
	        ],
	    },
	}

	actions = {
	    'backup_example': {
	    	'command': "cp /etc/example.conf /etc/example.conf.bak",
	    	'triggered': True,
	    },
	}

In this configuration, `/etc/example.conf` will always be copied before and only if it is changed. You would probably also want to set `cascade_skip` to `False` on the action so you can skip it in interactive mode when you're sure you don't need the backup copy.

Similar to `needed_by`, `precedes` can be used to define a `preceded_by` relationship from the opposite direction.

<br>

### unless

Another builtin item attribute is `unless`. For example, it can be used to construct a one-off file item where BundleWrap will only create the file once, but won't check or modify its contents once it exists.

	files = {
	    "/path/to/file": {
	        [...]
	        "unless": "test -x /path/to/file",
	    },
	}

This will run `test -x /path/to/file` before doing anything with the item. If the command returns 0, no action will be taken to "correct" the item.

Another common use for `unless` is with actions that perform some sort of install operation. In this case, the `unless` condition makes sure the install operation is only performed when it is needed instead of every time you run `bw apply`. In scenarios like this you will probably want to set `cascade_skip` to `False` so that skipping the installation (because the thing is already installed) will not cause every item that depends on the installed thing to be skipped. Example:

	actions = {
	    'download_thing': {
	    	'command': "wget http://example.com/thing.bin -O /opt/thing.bin && chmod +x /opt/thing.bin",
	    	'unless': "test -x /opt/thing.bin",
	    	'cascade_skip': False,
	    },
	    'run_thing': {
	        'command': "/opt/thing.bin",
	        'needs': ["action:download_thing"],
	    },
	}

If `action:download_thing` would not set `cascade_skip` to `False`, `action:run_thing` would only be executed once: directly after the thing has been downloaded. On subsequent runs, `action:download_thing` will fail the `unless` condition and be skipped. This would also cause all items that depend on it to be skipped, including `action:run_thing`.

<div class="alert alert-warning">The commands you choose for <code>unless</code> should not change the state of your node. Otherwise, running <code>bw verify</code> might unexpectedly interfere with your nodes.</div>

<br>

### cascade_skip

There are some situations where you don't want to default behavior of skipping everything that depends on a skipped item. That's where `cascade_skip` comes in. Set it to `False` and skipping an item won't skip those that depend on it. Note that items can be skipped

* interactively or
* because they haven't been triggered or
* because one of their dependencies failed or
* they failed their `unless` condition or
* because an [action](../items/action.md) had its `interactive` attribute set to `True` during a non-interactive run

The following example will offer to run an `apt-get update` before installing a package, but continue to install the package even if the update is declined interactively.

	actions = {
	    'apt_update': {
	        'cascade_skip': False,
	        'command': "apt-get update",
	    },
	}

	pkg_apt = {
	    'somepkg': {
	        'needs': ["action:apt_update"],
	    },
	}

`cascade_skip` defaults to `True`. However, if the item uses the `unless` attribute or is triggered, the default changes to `False`. Most of the time, this is what you'll want.

<br>

## Canned actions

Some item types have what we call "canned actions". Those are pre-defined actions attached directly to an item. Take a look at this example:

	svc_upstart = {'mysql': {'running': True}}

	files = {
	    "/etc/mysql/my.cnf": {
	        'source': "my.cnf",
	        'triggers': [
	            "svc_upstart:mysql:reload",  # this triggers the canned action
	        ],
	    },
	}

Canned actions always have to be triggered in order to run. In the example above, a change in the file `/etc/mysql/my.cnf` will trigger the `reload` action defined by the [svc_upstart item type](../items/svc_upstart.md) for the mysql service.

<br>

# metadata.py

Alongside `items.py` you may create another file called `metadata.py`. It can be used to do advanced processing of the metadata you configured for your nodes and groups. Specifically, it allows each bundle to modify metadata before `items.py` is evaluated.

This is accomplished through metadata processors. Metadata processors are functions that take the metadata dictionary generated so far as their single argument. You must then return a dictionary with any modifications you need to make plus at least one of several options:

	@metadata_processor
	def my_metadata_processor(metadata):
	    metadata["foo"] = node.name
	    return metadata, DONE

You must always return the modified metadata dictionary as the first element. After that, there are a few options you can return. Every metadata processor from every bundle is called *repeatedly* with the latest metadata dictionary until it indicates that it is done by returning the `DONE` option or until *all* remaining metadata processors return `RUN_ME_AGAIN`. You must always return one of `DONE` or `RUN_ME_AGAIN`. Use the latter if your metadata processor depends on metadata that is generated by another metadata processor (which may be called after yours). Here is another example:

	@metadata_processor
	def first_metadata_processor(metadata):
	    metadata["foo"] = node.name
	    return metadata, DONE

	@metadata_processor
	def second_metadata_processor(metadata):
	    if "foo" in metadata:
	        metadata["bar"] = metadata["foo"]
	        return metadata, DONE
	    else:
	        return metadata, RUN_ME_AGAIN

In this example, `"bar"` can only be set once `"foo"` is available and thus the `second_metadata_processor` has to wait and request to `RUN_ME_AGAIN` until `first_metadata_processor` ran. This is necessary because the running order of metadata processors is undefined.

<div class="alert alert-danger">To avoid deadlocks when accessing <strong>other</strong> nodes' metadata from within a metadata processor, use <code>other_node.partial_metadata</code> instead of <code>other_node.metadata</code>. For the same reason, always use the <code>metadata</code> parameter to access the current node's metadata, never <code>node.metadata</code>.</div>

Available options:

<table>
<tr><th>Option</th><th>Description</th></tr>
<tr><td><code>DONE</code></td><td>Indicates that this metadata processor has done all it can and need not be called again. Return this whenever possible.</td></tr>
<tr><td><code>RUN_ME_AGAIN</code></td><td>Indicates that this metadata processor is still waiting for metadata from another metadata processor to become available.</td></tr>
<tr><td><code>DEFAULTS</code></td><td>The returned metadata dictionary will only be used to provide default values. The actual metadata generated so far will be recursively merged into the returned dict.</td></tr>
<tr><td><code>OVERWRITE</code></td><td>The returned metadata dictionary will be recursively merged into the actual metadata generated so far (inverse of <code>DEFAULTS</code>).</td></tr>
</table>

Here is an example of how to use `DEFAULTS`:

	@metadata_processor
	def my_metadata_processor(metadata):
	    return {
	        "foo": {
	            "bar": 47,
	        },
	    }, DONE, DEFAULTS

This means `node.metadata["foo"]["bar"]` will be 47 by default, but can also be overridden in static metadata at the node/group level.

For your convenience, you can access `repo`, `node`, `metadata_processor` and all the options in `metadata.py` without importing them.
