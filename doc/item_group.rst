.. _item_group:

###########
Group items
###########

Manages system groups. Group members are managed through the :doc:`user <item_user>` item.

.. code-block:: python

    groups = {
        "acme": {
            "gid": 2342,
        },
    }

|

Attribute reference
-------------------

.. seealso::

   :ref:`The list of generic builtin item attributes <builtin_item_attributes>`

Required attributes
===================

``gid``
+++++++

Numerical ID of the group.
