.. _item_pkg_pacman:

################
Pkg_pacman items
################

Handles packages installed by ``pacman`` (e.g., Arch Linux).

.. code-block:: python

    pkg_pacman = {
        "foopkg": {
            "installed": True,  # default
        },
        "bar": {
            "installed": False,
        },
    }

.. warning::
    System updates on Arch Linux should *always* be performed manually and with great care. Thus, this item type installs packages with a simple ``pacman -S $pkgname`` instead of the commonly recommended ``pacman -Syu $pkgname``. You should *manually* do a full system update before installing new packages via Blockwart!


Attribute reference
-------------------


Optional attributes
===================

``installed``
+++++++++++++

``True`` when the package is expected to be present on the system; ``False`` if this package and all dependencies that are no longer needed should be removed.
