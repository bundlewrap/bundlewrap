.. _item_svc_systemd:

#####################
systemd service items
#####################

Handles services managed by systemd.

.. code-block:: python

    svc_systemd = {
        "fcron.service": {
            "running": True,  # default
        },
        "sgopherd.socket": {
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
