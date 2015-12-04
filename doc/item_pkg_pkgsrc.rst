.. _item_pkg_pkgsrc:

####################
pkgsrc package items
####################

Handles packages installed by ``pkgin`` for the portable package build system.

.. code-block:: python

    pkg_pkgsrc = {
        "foopkg": {
            "installed": True,  # default
        },
        "bar": {
            "installed": False,
        },
    }

Attribute reference
-------------------

.. seealso::

   :ref:`The list of generic builtin item attributes <builtin_item_attributes>`

Optional attributes
===================

``installed``
+++++++++++++

``True`` when the package is expected to be present on the system; ``False`` if it should be purged.
