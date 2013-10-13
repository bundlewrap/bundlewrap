.. _item_symlink:

#############
Symlink items
#############

.. code-block:: python

    symlinks = {
        "/some/symlink": {
            "group": "root",
            "owner": "root",
            "target": "/target/file",
        },
    }

Attribute reference
-------------------

``group``
+++++++++

Name of the group this symlink belongs to.

``owner``
+++++++++

Username of the symlink's owner.

``target``
++++++++++

File or directory this symlink points to. This attribute is required.
