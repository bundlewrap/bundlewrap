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

|

``stopstart``
=============

Stops and then starts the service. This is different from ``restart`` in that Upstart will pick up changes to the :file:`/etc/init/SERVICENAME.conf` file, while ``restart`` will continue to use the version of that file that the service was originally started with. See http://askubuntu.com/a/238069.
