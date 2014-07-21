.. _item_file:

##########
File items
##########

.. toctree::
	:hidden:

	item_file_templates

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
| ``any``            | only cares about file owner, group, and mode                               |
+--------------------+----------------------------------------------------------------------------+
| ``binary``         | file is uploaded verbatim, no content processing occurs                    |
+--------------------+----------------------------------------------------------------------------+
| ``jinja2``         | content is interpreted by the Jinja2 template engine                       |
+--------------------+----------------------------------------------------------------------------+
| ``mako`` (default) | content is interpreted by the Mako template engine                         |
+--------------------+----------------------------------------------------------------------------+
| ``text``           | like ``binary``, but will be diffed in interactive mode                    |
+--------------------+----------------------------------------------------------------------------+

.. note::

	In order to use Jinja2, you'll also need to install it manually, since BundleWrap doesn't explicitly depend on it::

		pip install Jinja2

|

``context``
+++++++++++

Only used with Mako templates. The values of this dictionary will be available from within the template as variables named after the respective keys.

|

``delete``
++++++++++

When set to ``True``, the path of this file will be removed. It doesn't matter if there is not a file but a directory or something else at this path. When using ``delete``, no other attributes are allowed.

|

``encoding``
++++++++++++

Encoding of the target file. Note that this applies to the remote file only, your template is still conveniently written in UTF-8 and will be converted by BundleWrap. Defaults to "utf-8". Other possible values (e.g. "latin-1") can be found `here <http://docs.python.org/2/library/codecs.html#standard-encodings>`_.

|

``group``
+++++++++

Name of the group this file belongs to. Defaults to ``None`` (don't care about group).

|

``mode``
++++++++

File mode as returned by :command:`stat -c %a <file>`. Defaults to ``None`` (don't care about mode).

|

``owner``
+++++++++

Username of the file's owner. Defaults to ``None`` (don't care about owner).

|

.. _file_item_source:

``source``
++++++++++

File name of the file template relative to the :file:`files` subdirectory of the current bundle. If this says ``my_template``, BundleWrap will look in :file:`bundles/my_bundle/files/my_template`.

.. seealso::

	:doc:`Writing file templates <item_file_templates>`
