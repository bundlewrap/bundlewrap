.. _action:

#######
Actions
#######

.. toctree::

Actions will be run on every ``bw apply``. They differ from items in that they cannot be "correct" in the first place. They can only succeed or fail.

.. code-block:: python

    actions = {
        'check_if_its_still_linux': {
            'command': "uname",
            'expected_return_code': 0,
            'expected_stdout': "Linux\n",
            'timing': "pre",
        },
    }

|

Attribute reference
-------------------

``command``
+++++++++++

The only required attribute. This is the command that will be run on the node with root privileges.

|

``expected_return_code``
++++++++++++++++++++++++

Defaults to ``0``. If the return code of your command is anything else, the action is considered failed.

|

``expected_stdout``
+++++++++++++++++++

If this is given, the stdout output of the command must match the given string or the action is considered failed.

|

``expected_stderr``
+++++++++++++++++++

Same as ``expected_stdout``, but with stderr.

|

``timing``
++++++++++

Acceptable values are ``"pre"``, ``"post"`` or ``"triggered"``. Choose ``pre`` or ``post`` depending on whether you want the action to be run before or after items are applied. When set to ``triggered``, the action will only be executed by :ref:`action_triggers`. Defaults to ``"pre"``.

|

``unless``
++++++++++

Works just like the ``unless`` attribute :ref:`on items <unless>`.
