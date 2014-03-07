.. _item_svc_upstart:

#####################
Upstart service items
#####################

Handles services managed by Upstart.

.. code-block:: python

    svc_upstart = {
        "gunicorn": {
            "running": True,  # default
        },
        "celery": {
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
