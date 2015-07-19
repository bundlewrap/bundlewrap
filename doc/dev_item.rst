.. _dev_item:

=================
Custom item types
=================

.. toctree::


Step 0: Understand sdicts
-------------------------

To represent supposed vs. actual state, BundleWrap uses state dicts (sdicts for short). These are
normal Python dictionaries with some restrictions:

- keys must be Unicode text
- every value must be of one of these simple data types:

  - bool
  - float
  - int
  - Unicode text
  - None

- ...or a list/tuple containing only instances of one of the types above

Additional information can be stored in sdicts by using keys that start with an underscore. You may only use this for caching purposes (e.g. storing rendered file template content while the "real" sdict information only contains a hash of this content). BundleWrap will ignore these keys and hide them from the user. The type restrictions noted above do not apply, but everything must be pickleable.


Step 1: Create an item module
-----------------------------

Create a new file called :file:`/your/bundlewrap/repo/items/foo.py`. You can use this as a template:

.. code-block:: python

    from bundlewrap.items import Item, ItemStatus


    class Foo(Item):
        """
        A foo.
        """
        BLOCK_CONCURRENT = []
        BUNDLE_ATTRIBUTE_NAME = "foo"
        NEEDS_STATIC = []
        ITEM_ATTRIBUTES = {
            'attribute': "default value",
        }
        ITEM_TYPE_NAME = "foo"
        REQUIRED_ATTRIBUTES = ['attribute']

        def __repr__(self):
            return "<Foo attribute:{}>".format(self.attributes['attribute'])

        def sdict(self):
            """
            Return an sdict that describes the target state of this item
            as configured in the repo. An empty dict means that the item
            should not exist.

            Implementing this method is optional. The default implementation
            uses the attributes as defined in the bundle.
            """
            raise NotImplementedError

        def sdict_actual(self):
            """
            Return an sdict that describes the actual state of this item
            on the node. An empty dict means that the item does not exist
            on the node.

            For the item to validate as correct, this sdict and the one
            produced by self.sdict() have to be identical.
            """
            raise NotImplementedError

        def sdict_verbose(self, sdict, keys, actual):
            """
            Return an sdict based on the given one that is suitable for
            displaying information during interactive apply mode.
            The keys parameter indicates which keys are incorrect. It is
            sufficient to return an sdict that only represents these
            keys. The boolean actual parameter indicates if the source
            sdict is based on de facto node state (True) or taken from
            the repo (False).

            Implementing this method is optional. The default implementation
            returns the sdict unaltered.
            """
            raise NotImplementedError

        def fix(self, keys, sdict, sdict_actual):
            """
            Do whatever is necessary to correct this item. The keys
            argument is a list of keys that differ in the two given
            sdicts.
            """
            raise NotImplementedError


|

Step 2: Define attributes
-------------------------

``BUNDLE_ATTRIBUTE_NAME`` is the name of the variable defined in a bundle module that holds the items of this type. If your bundle looks like this:

.. code-block:: python

   foo = { [...] }

...then you should put ``BUNDLE_ATTRIBUTE_NAME = "foo"`` here.


``NEEDS_STATIC`` is a list of hard-wired dependencies for all intances of your item. For example, all services inherently depend on all packages (because you can't start the service without installing its package first). Most of the time, this will be a wildcard dependency on a whole type of items, not a specific one:

.. code-block:: python

    NEEDS_STATIC = ["file:/etc/hosts", "user:"]  # depends on /etc/hosts and all users


``ITEM_ATTRIBUTES`` is a dictionary of the attributes users will be able to configure for your item. For files, that would be stuff like owner, group, and permissions. Every attribute (even if it's mandatory) needs a default value, ``None`` is totally acceptable:

.. code-block:: python

    ITEM_ATTRIBUTES = {'attr1': "default1"}


``ITEM_TYPE_NAME`` sets the first part of an items ID. For the file items, this is "file". Therefore, file ID look this this: ``file:/path``. The second part is the name a user assigns to your item in a bundle. Example:

.. code-block:: python

    ITEM_TYPE_NAME = "foo"


``BLOCK_CONCURRENT`` is a list of item types (e.g. ``pkg_apt``), that cannot be applied in parallel with this type of item. May include this very item type itself. For most items this is not an issue (e.g. creating multiple files at the same time), but some types of items have to be applied sequentially (e.g. package managers usually employ locks to ensure only one package is installed at a time):

.. code-block:: python

    BLOCK_CONCURRENT = ["pkg_apt"]


``REQUIRED_ATTRIBUTES`` is a list of attribute names that must be set on each item of this type. If BundleWrap encounters an item without all these attributes during bundle inspection, an exception will be raised. Example:

.. code-block:: python

    REQUIRED_ATTRIBUTES = ['attr1', 'attr2']

|

Step 3: Implement methods
-------------------------

You should probably start with ``sdict_actual``. Use ``self.node.run("command")`` to run shell commands on the current node and check the ``stdout`` property of the returned object.

The only other method you have to implement is ``fix``. It doesn't have to return anything and just uses ``self.node.run()`` to fix the item. To do this efficiently, it may use the provided parameters indicating which keys differ between the should-be sdict and the actual one. Both sdicts are also provided in case you need to know their values.

If you're having trouble, try looking at the `source code for the items that come with BundleWrap <https://github.com/bundlewrap/bundlewrap/tree/master/src/bundlewrap/items>`_. The ``pkg_*`` items are pretty simple and easy to understand while ``files`` is the most complex to date. Or just drop by on `IRC <irc://chat.freenode.net/bundlewrap>`_, we're glad to help.
