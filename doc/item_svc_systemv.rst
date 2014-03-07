.. _item_svc_systemv:

######################
System V service items
######################

Handles services managed by traditional System V init scripts.

.. code-block:: python

    svc_systemv = {
        "apache2": {
            "running": True,  # default
        },
        "mysql": {
            "running": False,
        },
    }

|

Attribute reference
-------------------

.. seealso::

   :ref:`The list of generic builtin item attributes <builtin_item_attributes>`

Optional attributes
===================

``running``
+++++++++++

``True`` if the service is expected to be running on the system; ``False`` if it should be stopped.
