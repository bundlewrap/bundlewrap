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
            "encoding": "utf-8",
            "source": "my_template",
        },
    }

|

Attribute reference
-------------------

.. seealso::

   :ref:`The list of generic builtin item attributes <builtin_item_attributes>`

``content``
+++++++++++

May be used instead of ``source`` to provide file content without a template file. Must be a UTF-8 string. Defaults to ``""``.

|

``content_type``
++++++++++++++++

How the file pointed to by ``source`` or the string given to ``content`` should be interpreted.

+--------------------+----------------------------------------------------------------------------+
| Value              | Effect                                                                     |
+====================+============================================================================+
| ``binary``         | file is uploaded verbatim, no content processing occurs                    |
+--------------------+----------------------------------------------------------------------------+
| ``mako`` (default) | content is interpreted by the Mako template engine                         |
+--------------------+----------------------------------------------------------------------------+
| ``text``           | like ``binary``, but will be diffed in interactive mode                    |
+--------------------+----------------------------------------------------------------------------+

|

``context``
+++++++++++

Only used with Mako templates. The values of this dictionary will be available from within the template as variables named after the respective keys.

|

``encoding``
++++++++++++

Encoding of the target file. Note that this applies to the remote file only, your template is still conveniently written in UTF-8 and will be converted by Blockwart. Defaults to "utf-8". Other possible values (e.g. "latin-1") can be found `here <http://docs.python.org/2/library/codecs.html#standard-encodings>`_.

|

``group``
+++++++++

Name of the group this file belongs to. Defaults to ``root``.

|

``mode``
++++++++

File mode as returned by ``stat -c %a <file>``.

|

``owner``
+++++++++

Username of the file's owner. Defaults to ``root``.

|

``source``
++++++++++

File name of the file template relative to the ``files`` subdirectory of the current bundle. If this says ``my_template``, Blockwart will look in ``bundles/my_bundle/files/my_template``.
