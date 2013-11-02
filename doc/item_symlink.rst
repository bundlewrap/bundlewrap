.. _item_symlink:

#############
Symlink items
#############

.. toctree::

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


Required attributes
===================

``target``
++++++++++

File or directory this symlink points to. This attribute is required.


Optional attributes
===================

``group``
+++++++++

Name of the group this symlink belongs to. Defaults to ``root``.

``owner``
+++++++++

Username of the symlink's owner. Defaults to ``root``.
