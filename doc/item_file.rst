.. _item_file:

##########
File items
##########

Manages regular files.

.. code-block:: python

    files = {
        "/path/to/file": {
            "mode": "0644",
            "owner": "root",
            "group": "root",
            "content_type": "mako",
            "source": "my_template",
        },
    }

Attribute reference
-------------------

``content_type``
++++++++++++++++

How the file pointed to by ``source`` should be interpreted.

+--------------------+----------------------------------------------------------------------------+
| Value              | Effect                                                                     |
+====================+============================================================================+
| ``binary``         | file is uploaded verbatim, no content processing occurs                    |
+--------------------+----------------------------------------------------------------------------+
| ``mako`` (default) | content is interpreted by the Mako template engine                         |
+--------------------+----------------------------------------------------------------------------+

``group``
+++++++++

Name of the group this file belongs to. Defaults to ``root``.

``mode``
++++++++

File mode as returned by ``stat -c %a <file>``.

``owner``
+++++++++

Username of the file's owner. Defaults to ``root``.

``source``
++++++++++

File name of the file template relative to the ``files`` subdirectory of the current bundle. If this says ``my_template``, Blockwart will look in ``bundles/my_bundle/files/my_template``.
