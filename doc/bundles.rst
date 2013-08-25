.. _bundles:

================
Bundle reference
================

.. toctree::
    :hidden:

    item_directory
    item_file

Bundles are subdirectories of the ``bundles/`` directory of your Blockwart repository. Within each bundle, there must be a file called ``bundle.py``. They define any number of magic attributes that are automatically processed by Blockwart. Each attribute is a dictionary mapping an item name (such as a file name) to a dictionary of attributes (e.g. file ownership information).

A typical bundle might look like this::

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

+--------------------------------------+------------------+------------------------------------------------------------------------+
| Type name                            | Bundle attribute | Purpose                                                                |
+======================================+==================+========================================================================+
| :doc:`directory <item_directory>`    | ``directories``  | Manages permissions and ownership for directories                      |
+--------------------------------------+------------------+------------------------------------------------------------------------+
| :doc:`file <item_file>`              | ``files``        | Manages contents, permissions, and ownership for files                 |
+--------------------------------------+------------------+------------------------------------------------------------------------+
| :doc:`pkg_apt <item_pkg_apt>`        | ``pkg_apt``      | Installs and removes packages with APT                                 |
+--------------------------------------+------------------+------------------------------------------------------------------------+

Builtin attributes
------------------

There are also attributes that can be applied to any kind of item.

Item dependencies
#################

One such attribute is ``depends``. It allows for setting up dependencies between items. This is not something you will have to to very often, because there are already implicit dependencies between items types (e.g. all files depend on all directories). Here are two examples::

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
