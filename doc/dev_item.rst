.. _dev_item:

=================
Custom item types
=================

.. toctree::

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

        def ask(self, status):
            """
            Returns a string asking the user if this item should be
            implemented.
            """
            return ""

        def fix(self, status):
            """
            Do whatever is necessary to correct this item.
            """
            raise NotImplementedError

        def get_status(self):
            """
            Returns an ItemStatus instance describing the current status of
            the item on the actual node. Must not be cached.
            """
            return ItemStatus(
                correct=True,
                description="No description available.",
                info={},
            )

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

You should probably start with ``get_status``. Use ``self.node.run("command")`` to run shell commands on the current node and check the ``stdout`` property of the returned object. The info dict passed to ``ItemStatus`` can be filled with arbitrary information on how to efficiently fix the item.

Next up is the ``ask`` method. It must return a string containing all information a user needs in interactive mode to decide whether they want to apply the item or not and offer a preview of all changes that would be made.

Finally, the ``fix`` method doesn't have to return anything and just uses ``self.node.run()`` to fix the item. To do this efficiently, it may use the ``status.info`` dict you built earlier.
