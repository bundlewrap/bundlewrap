.. _item_svc_smf:

######################
SMF service items
######################

Handles services managed by the service management facility.

.. code-block:: python

    svc_smf = {
        "apache2": {
            "running": True,  # default
        },
        "svc:/network/smtp:sendmail": {
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
