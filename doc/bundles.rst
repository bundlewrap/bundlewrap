.. _bundles:

=======
Bundles
=======

.. toctree::
    :hidden:

    actions
    item_directory
    item_file
    item_group
    item_pkg_apt
    item_pkg_pacman
    item_svc_upstart
    item_symlink
    item_user

Bundles are subdirectories of the ``bundles/`` directory of your Blockwart repository. Within each bundle, there must be a file called ``bundle.py``. They define any number of magic attributes that are automatically processed by Blockwart. Each attribute is a dictionary mapping an item name (such as a file name) to a dictionary of attributes (e.g. file ownership information).

A typical bundle might look like this:

.. code-block:: python

    files = {
        '/etc/hosts': {
             'owner': "root",
             'group': "root",
             'mode': "664",
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

Item types
----------

This table lists all item types included in Blockwart along with the bundle attributes they understand.

.. raw:: html

   <style type="text/css">.wy-table-responsive table td { vertical-align: top !important; white-space: normal !important; }</style>

+---------------------------------------+------------------+----------------------------------------------------------------------------------------+
| Type name                             | Bundle attribute | Purpose                                                                                |
+=======================================+==================+========================================================================================+
| :doc:`action <actions>`               | ``actions``      | While not technically an item, actions allow you to run commands on every ``bw apply`` |
+---------------------------------------+------------------+----------------------------------------------------------------------------------------+
| :doc:`directory <item_directory>`     | ``directories``  | Manages permissions and ownership for directories                                      |
+---------------------------------------+------------------+----------------------------------------------------------------------------------------+
| :doc:`file <item_file>`               | ``files``        | Manages contents, permissions, and ownership for files                                 |
+---------------------------------------+------------------+----------------------------------------------------------------------------------------+
| :doc:`group <item_group>`             | ``groups``       | Manages groups by wrapping ``groupadd``, ``groupmod`` and ``groupdel``                 |
+---------------------------------------+------------------+----------------------------------------------------------------------------------------+
| :doc:`pkg_apt <item_pkg_apt>`         | ``pkg_apt``      | Installs and removes packages with APT                                                 |
+---------------------------------------+------------------+----------------------------------------------------------------------------------------+
| :doc:`pkg_pacman <item_pkg_pacman>`   | ``pkg_pacman``   | Installs and removes packages with pacman                                              |
+---------------------------------------+------------------+----------------------------------------------------------------------------------------+
| :doc:`svc_upstart <item_svc_upstart>` | ``svc_upstart``  | Starts and stops services with Upstart                                                 |
+---------------------------------------+------------------+----------------------------------------------------------------------------------------+
| :doc:`symlink <item_symlink>`         | ``symlinks``     | Manages symbolic links and their ownership                                             |
+---------------------------------------+------------------+----------------------------------------------------------------------------------------+
| :doc:`user <item_user>`               | ``users``        | Manages users by wrapping ``useradd``, ``usermod`` and ``userdel``                     |
+---------------------------------------+------------------+----------------------------------------------------------------------------------------+

Builtin attributes
------------------

There are also attributes that can be applied to any kind of item.

Item dependencies
#################

One such attribute is ``depends``. It allows for setting up dependencies between items. This is not something you will have to to very often, because there are already implicit dependencies between items types (e.g. all files depend on all directories). Here are two examples:

.. code-block:: python

    my_items = {
        'item1': {
            [...]
            'depends': [
                'file:/etc/foo.conf',
            ],
        },
        'item2': {
            ...
            'depends': [
                'user:',
            ],
        }
    }

The first item (``item1``, specific attributes have been omitted) depends on a file called ``/etc/foo.conf``, while ``item2`` depends on all users.
