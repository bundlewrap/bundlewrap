.. _item_pkg_apt:

#################
yum package items
#################

Handles packages installed by ``yum`` on RPM-based systems.

.. code-block:: python

    pkg_yum = {
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

``True`` when the package is expected to be present on the system; ``False`` if it should be removed.
