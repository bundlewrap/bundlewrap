.. _bundles:

=======
Bundles
=======

.. toctree::
	:hidden:

	item_action
	item_directory
	item_file
	item_group
	item_pkg_apt
	item_pkg_pacman
	item_pkg_pip
	item_pkg_yum
	item_pkg_zypper
	item_postgres_db
	item_postgres_role
	item_svc_upstart
	item_svc_systemd
	item_svc_systemv
	item_symlink
	item_user

Bundles are subdirectories of the :file:`bundles/` directory of your BundleWrap repository. Within each bundle, there must be a file called :file:`bundle.py`. They define any number of magic attributes that are automatically processed by BundleWrap. Each attribute is a dictionary mapping an item name (such as a file name) to a dictionary of attributes (e.g. file ownership information).

A typical bundle might look like this:

.. code-block:: python

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

This bundle defines the attributes ``files`` and ``users``. Within the ``users`` attribute, there are two ``user`` items. Each item maps its name to a dictionary that is understood by the specific kind of item. Below you will find a reference of all builtin item types and the attributes they understand. You can also :doc:`define your own item types <dev_item>`.

|

.. _item_types:

Item types
----------

This table lists all item types included in BundleWrap along with the bundle attributes they understand.

.. raw:: html

	<style type="text/css">.wy-table-responsive table td { vertical-align: top !important; white-space: normal !important; }</style>

+-------------------------------------------+--------------------+----------------------------------------------------------------------------------------+
| Type name                                 | Bundle attribute   | Purpose                                                                                |
+===========================================+====================+========================================================================================+
| :doc:`action <item_action>`               | ``actions``        | Actions allow you to run commands on every ``bw apply``                                |
+-------------------------------------------+--------------------+----------------------------------------------------------------------------------------+
| :doc:`directory <item_directory>`         | ``directories``    | Manages permissions and ownership for directories                                      |
+-------------------------------------------+--------------------+----------------------------------------------------------------------------------------+
| :doc:`file <item_file>`                   | ``files``          | Manages contents, permissions, and ownership for files                                 |
+-------------------------------------------+--------------------+----------------------------------------------------------------------------------------+
| :doc:`group <item_group>`                 | ``groups``         | Manages groups by wrapping ``groupadd``, ``groupmod`` and ``groupdel``                 |
+-------------------------------------------+--------------------+----------------------------------------------------------------------------------------+
| :doc:`pkg_apt <item_pkg_apt>`             | ``pkg_apt``        | Installs and removes packages with APT                                                 |
+-------------------------------------------+--------------------+----------------------------------------------------------------------------------------+
| :doc:`pkg_pacman <item_pkg_pacman>`       | ``pkg_pacman``     | Installs and removes packages with pacman                                              |
+-------------------------------------------+--------------------+----------------------------------------------------------------------------------------+
| :doc:`pkg_pip <item_pkg_pip>`             | ``pkg_pip``        | Installs and removes Python packages with pip                                          |
+-------------------------------------------+--------------------+----------------------------------------------------------------------------------------+
| :doc:`pkg_yum <item_pkg_yum>`             | ``pkg_yum``        | Installs and removes packages with yum                                                 |
+-------------------------------------------+--------------------+----------------------------------------------------------------------------------------+
| :doc:`pkg_zypper <item_pkg_zypper>`       | ``pkg_zypper``     | Installs and removes packages with zypper                                              |
+-------------------------------------------+--------------------+----------------------------------------------------------------------------------------+
| :doc:`postgres_db <item_postgres_db>`     | ``postgres_dbs``   | Manages Postgres databases                                                             |
+-------------------------------------------+--------------------+----------------------------------------------------------------------------------------+
| :doc:`postgres_role <item_postgres_role>` | ``postgres_roles`` | Manages Postgres roles                                                                 |
+-------------------------------------------+--------------------+----------------------------------------------------------------------------------------+
| :doc:`pkg_pip <item_pkg_pip>`             | ``pkg_pip``        | Installs and removes Python packages with pip                                          |
+-------------------------------------------+--------------------+----------------------------------------------------------------------------------------+
| :doc:`svc_upstart <item_svc_upstart>`     | ``svc_upstart``    | Starts and stops services with Upstart                                                 |
+-------------------------------------------+--------------------+----------------------------------------------------------------------------------------+
| :doc:`svc_systemd <item_svc_systemd>`     | ``svc_systemd``    | Starts and stops services with systemd                                                 |
+-------------------------------------------+--------------------+----------------------------------------------------------------------------------------+
| :doc:`svc_systemv <item_svc_systemv>`     | ``svc_systemv``    | Starts and stops services with traditional System V init scripts                       |
+-------------------------------------------+--------------------+----------------------------------------------------------------------------------------+
| :doc:`symlink <item_symlink>`             | ``symlinks``       | Manages symbolic links and their ownership                                             |
+-------------------------------------------+--------------------+----------------------------------------------------------------------------------------+
| :doc:`user <item_user>`                   | ``users``          | Manages users by wrapping ``useradd``, ``usermod`` and ``userdel``                     |
+-------------------------------------------+--------------------+----------------------------------------------------------------------------------------+

|

.. _builtin_item_attributes:

Builtin attributes
------------------

There are also attributes that can be applied to any kind of item.

``needs``
#########

One such attribute is ``needs``. It allows for setting up dependencies between items. This is not something you will have to to very often, because there are already implicit dependencies between items types (e.g. all files depend on all users). Here are two examples:

.. code-block:: python

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

The first item (``item1``, specific attributes have been omitted) depends on a file called :file:`/etc/foo.conf`, while ``item2`` depends on all APT packages being installed and every item in the foo bundle.

|

``needed_by``
#############

This attribute is an alternative way of defining dependencies. It works just like ``needs``, but in the other direction. There are only three scenarios where you should use ``needed_by`` over ``needs``:

* if you need all items a certain type to depend on something or
* if you need all items in a bundle to depend on something or
* if you need an item in a bundle you can't edit (e.g. because it's provided by a community-maintained :doc:`plugin <plugins>`) to depend on something in your bundles

|

.. _triggers:

``triggers`` and ``triggered``
##############################

In some scenarios, you may want to execute an :ref:`action <item_action>` only when an item is fixed (e.g. restart a daemon after a config file has changed or run ``postmap`` after updating an alias file). To do this, BundleWrap has the builtin atttribute ``triggers``. You can use it to point to any item that has its ``triggered`` attribute set to ``True``. Such items will only be checked (or in the case of actions: run) if the triggering item is fixed (or a triggering action completes successfully).

.. code-block:: python

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

The above example will run :command:`service daemon restart` every time BundleWrap successfully applies a change to :file:`/etc/daemon.conf`. If an action is triggered multiple times, it will only be run once.

Similar to ``needed_by``, ``triggered_by`` can be used to define a ``triggers`` relationship from the opposite direction.

|

.. _preceded_by:

``preceded_by``
###############

Operates like ``triggers``, but will apply the triggered item *before* the triggering item. Let's look at an example:

.. code-block:: python

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

In this configuration, ``/etc/example.conf`` will always be copied before and only if it is changed. You would probably also want to set ``cascade_skip`` to ``False`` on the action so you can skip it in interactive mode when you're sure you don't need the backup copy.

Similar to ``needed_by``, ``precedes`` can be used to define a ``preceded_by`` relationship from the opposite direction.

|

.. _unless:

``unless``
##########

Another builtin item attribute is ``unless``. For example, it can be used to construct a one-off file item where BundleWrap will only create the file once, but won't check or modify its contents once it exists.

.. code-block:: python

	files = {
	    "/path/to/file": {
	        [...]
	        "unless": "test -x /path/to/file",
	    },
	}

This will run :command:`test -x /path/to/file` before doing anything with the item. If the command returns 0, no action will be taken to "correct" the item.

.. note::

	Another common use for ``unless`` is with actions that perform some sort of install operation. In this case, the ``unless`` condition makes sure the install operation is only performed when it is needed instead of every time you run :command:`bw apply`. In scenarios like this you will probably want to set ``cascade_skip`` to ``False`` so that skipping the installation (because the thing is already installed) will not cause every item that depends on the installed thing to be skipped. Example::

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

	If ``action:download_thing`` would not set ``cascade_skip`` to ``False``, ``action:run_thing`` would only be executed once: directly after the thing has been downloaded. On subsequent runs, ``action:download_thing`` will fail the ``unless`` condition and be skipped. This would also cause all items that depend on it to be skipped, including ``action:run_thing``.

|

``cascade_skip``
################

There are some situations where you don't want to default behavior of skipping everything that depends on a skipped item. That's where ``cascade_skip`` comes in. Set it to ``False`` and skipping an item won't skip those that depend on it. Note that items can be skipped

* interactively or
* because they haven't been :ref:`triggered <triggers>` or
* because one of their dependencies failed or
* they failed their :ref:`'unless' condition<unless>` or
* because an :doc:`action <item_action>` had its ``interactive`` attribute set to ``True`` during a non-interactive run

The following example will offer to run an ``apt-get update`` before installing a package, but continue to install the package even if the update is declined interactively.

.. code-block:: python

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

|

.. _canned_actions:

Canned actions
--------------

Some item types have what we call "canned actions". Those are pre-defined actions attached directly to an item. Take a look at this example:

.. code-block:: python

	svc_upstart = {'mysql': {'running': True}}

	files = {
	    "/etc/mysql/my.cnf": {
	        'source': "my.cnf",
	        'triggers': [
	            "svc_upstart:mysql:reload",  # this triggers the canned action
	        ],
	    },
	}

Canned actions always have to be triggered in order to run. In the example above, a change in the file :file:`/etc/mysql/my.cnf` will trigger the ``reload`` action defined by the :doc:`svc_upstart item type <item_svc_upstart>` for the mysql service.

|

.. _item_generators:

Item generators
---------------

.. note::

	This is an advanced feature. You should already be very familiar with BundleWrap before using this.

In addition to the bundle attributes listed in the table above, you can define an attribute called ``item_generators`` as a list of strings formatted as ``module.function`` where *module* is the name of a file in the ``libs/`` :doc:`subdirectory <libs>` of your repo (without the ``.py`` extension) and *function* is the name of a function in that file.

This function can be used to dynamically create items based on the existence of other items. Here is an example that will automatically generate a personal screenrc file for each user on the node:

.. code-block:: python

	def my_item_generator(node, bundle, item):
	    generated_items = {'files': {}}
	    if item.ITEM_TYPE_NAME == 'user':
	        file_path = "/home/{}/.screenrc".format(item.name)
	        generated_items['files'][file_path] = {
	            'content': ...,
	        }
	    return generated_items

As you can see, the item generator function is passed the current node, the calling bundle, and an item. It is called once for *every* item defined the usual way in a bundle or generated by an item generator (including itself!).

.. warning::
	This means that you need to make sure your item generators don't generate items that will cause an endless loop of generated items (in the example above, it would be inadvisable to write another item generator that creates a user for every file).

Item generators must return a dictionary that looks like the dictionaries in a bundle, using a top-level dictionary to group item types instead of attributes. In the above example, we create a dictionary like this:

.. code-block:: python

	{
	    'files': {
	        "/home/jdoe/.screenrc": {
	            ...
	        },
	    },
	}

The equivalent bundle syntax being:

.. code-block:: python

	files = {
	    "/home/jdoe/.screenrc": {
	        ...
	    },
	}

|
