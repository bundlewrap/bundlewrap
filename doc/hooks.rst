.. _hooks:

=====
Hooks
=====

Hooks enable you to execute custom code at certain points during a Blockwart run. This is useful for integrating with other systems e.g. for team notifications, logging or statistics.

To use hooks, you need to create a subdirectory in your repo called ``hooks``. In that directory you can place an arbitrary number of Python source files. If those source files define certain functions, these functions will be called at the appropriate time.


Example
-------

``hooks/my_awesome_notification.py``:

.. code-block:: python

    from my_awesome_notification_system import post_message

    def node_apply_start(node, interactive):
        post_message("Starting apply on {}, everything is gonna be OK!".format(node.name))


Functions
---------

This is a list of all functions a hook file may implement.


``apply_start``
###############

.. py:function:: apply_start(target, interactive)

    Called when you start a ``bw apply`` command.

    :param str target: The group or node name you gave on the command line.
    :param bool interactive: Indicates whether the apply is interactive or not.

``apply_end``
#############

.. py:function:: apply_end(target, time_elapsed)

    Called when a ``bw apply`` command completes.

    :param str target: The group or node name you gave on the command line.
    :param timedelta time_elapsed: How long the apply took.

item_apply_start
item_apply_end
item_apply_aborted
node_apply_start
node_apply_end
node_run_start
node_run_end
run_start
run_end
