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

.. seealso::

   :ref:`The list of generic builtin item attributes <builtin_item_attributes>`

Required attributes
===================

``target``
++++++++++

File or directory this symlink points to. This attribute is required.


Optional attributes
===================

``group``
+++++++++

Name of the group this symlink belongs to. Defaults to ``root``. Defaults to ``None`` (don't care about group).

``owner``
+++++++++

Username of the symlink's owner. Defaults to ``root``. Defaults to ``None`` (don't care about owner).
