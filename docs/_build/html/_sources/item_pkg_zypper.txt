.. _item_pkg_zypper:

####################
zypper package items
####################

Handles packages installed by ``zypper`` on SUSE-based systems.

.. code-block:: python

    pkg_zypper = {
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
