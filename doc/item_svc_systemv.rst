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


Optional attributes
===================

``running``
+++++++++++

``True`` if the service is expected to be running on the system; ``False`` if it should be stopped.
