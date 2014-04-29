.. _item_pkg_pacman:

####################
Pacman package items
####################

Handles packages installed by :command:`pacman` (e.g., Arch Linux).

.. code-block:: python

    pkg_pacman = {
        "foopkg": {
            "installed": True,  # default
        },
        "bar": {
            "installed": False,
        },
        "somethingelse": {
            "tarball": "something-1.0.pkg.tar.gz",
        }
    }

.. warning::
    System updates on Arch Linux should *always* be performed manually and with great care. Thus, this item type installs packages with a simple ``pacman -S $pkgname`` instead of the commonly recommended ``pacman -Syu $pkgname``. You should *manually* do a full system update before installing new packages via Blockwart!


Attribute reference
-------------------

.. seealso::

   :ref:`The list of generic builtin item attributes <builtin_item_attributes>`

Optional attributes
===================

``installed``
+++++++++++++

``True`` when the package is expected to be present on the system; ``False`` if this package and all dependencies that are no longer needed should be removed.

``tarball``
+++++++++++

Upload a local file to the node and install it using :command:`pacman -U`. The value of ``tarball`` must point to a file relative to the ``pkg_pacman`` subdirectory of the current bundle.
