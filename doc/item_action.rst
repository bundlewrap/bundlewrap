.. _item_action:

#######
Actions
#######

.. toctree::

Actions will be run on every ``bw apply``. They differ from regular items in that they cannot be "correct" in the first place. They can only succeed or fail.

.. code-block:: python

    actions = {
        'check_if_its_still_linux': {
            'command': "uname",
            'expected_return_code': 0,
            'expected_stdout': "Linux\n",
        },
    }

|

Attribute reference
-------------------

.. seealso::

   :ref:`The list of generic builtin item attributes <builtin_item_attributes>`

``command``
+++++++++++

The only required attribute. This is the command that will be run on the node with root privileges.

|

``expected_return_code``
++++++++++++++++++++++++

Defaults to ``0``. If the return code of your command is anything else, the action is considered failed. You can also set this to ``None`` and any return code will be accepted.

|

``expected_stdout``
+++++++++++++++++++

If this is given, the stdout output of the command must match the given string or the action is considered failed.

|

``expected_stderr``
+++++++++++++++++++

Same as ``expected_stdout``, but with stderr.

|

``interactive``
+++++++++++++++

If set to ``True``, this action will be skipped in non-interactive mode. If set to ``False``, this action will always be executed without asking (even in interactive mode). Defaults to ``None``.

.. warning::

	Think hard before setting this to ``False``. People might assume that interactive mode won't do anything without their consent.
