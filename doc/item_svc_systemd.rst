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

.. seealso::

   :ref:`The list of generic builtin item attributes <builtin_item_attributes>`

Optional attributes
===================

``running``
+++++++++++

``True`` if the service is expected to be running on the system; ``False`` if it should be stopped.

|

Canned actions
--------------

.. seealso::

   :ref:`Explanation of how canned actions work <canned_actions>`

``reload``
==========

Reloads the service.

|

``restart``
===========

Restarts the service.
