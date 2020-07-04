# Hooks

Hooks enable you to execute custom code at certain points during a BundleWrap run. This is useful for integrating with other systems e.g. for team notifications, logging or statistics.

To use hooks, you need to create a subdirectory in your repo called `hooks`. In that directory you can place an arbitrary number of Python source files. If those source files define certain functions, these functions will be called at the appropriate time.


## Example

`hooks/my_awesome_notification.py`:

    from my_awesome_notification_system import post_message

    def node_apply_start(repo, node, interactive=False, **kwargs):
        post_message("Starting apply on {}, everything is gonna be OK!".format(node.name))

<div class="alert alert-warning">Always define your hooks with <code>**kwargs</code> so we can pass in more information in future updates without breaking your hook.</div>

<br>

## Functions

This is a list of all functions a hook file may implement.

---

**`action_run_start(repo, node, item, **kwargs)`**

Called each time a `bw apply` command reaches a new action.

`repo` The current repository (instance of `bundlewrap.repo.Repository`).

`node` The current node (instance of `bundlewrap.node.Node`).

`item` The current action.

---

**`action_run_end(repo, node, item, duration=None, status=None, **kwargs)`**

Called each time a `bw apply` command completes processing an action.

`repo` The current repository (instance of `bundlewrap.repo.Repository`).

`node` The current node (instance of `bundlewrap.node.Node`).

`item` The current action.

`duration` How long the action was running (timedelta).

`status`: One of `bundlewrap.items.Item.STATUS_FAILED`, `bundlewrap.items.Item.STATUS_SKIPPED`, or `bundlewrap.items.Item.STATUS_ACTION_SUCCEEDED`.

---

**`apply_start(repo, target, nodes, interactive=False, **kwargs)`**

Called when you start a `bw apply` command.

`repo` The current repository (instance of `bundlewrap.repo.Repository`).

`target` The group or node name you gave on the command line.

`nodes` A list of node objects affected (list of `bundlewrap.node.Node` instances).

`interactive` Indicates whether the apply is interactive or not.

To abort the entire apply operation:

```
from bundlewrap.exceptions import GracefulApplyException
raise GracefulApplyException("reason goes here")
```

---

**`apply_end(repo, target, nodes, duration=None, **kwargs)`**

Called when a `bw apply` command completes.

`repo` The current repository (instance of `bundlewrap.repo.Repository`).

`target` The group or node name you gave on the command line.

`nodes` A list of node objects affected (list of `bundlewrap.node.Node` instances).

`duration` How long the apply took (timedelta).

---

**`item_apply_start(repo, node, item, **kwargs)`**

Called each time a `bw apply` command reaches a new item.

`repo` The current repository (instance of `bundlewrap.repo.Repository`).

`node` The current node (instance of `bundlewrap.node.Node`).

`item` The current item.

---

**`item_apply_end(repo, node, item, duration=None, status_code=None, status_before=None, status_after=None, **kwargs)`**

Called each time a `bw apply` command completes processing an item.

`repo` The current repository (instance of `bundlewrap.repo.Repository`).

`node` The current node (instance of `bundlewrap.node.Node`).

`item` The current item.

`duration` How long the apply took (timedelta).

`status_code` One of `bundlewrap.items.Item.STATUS_FAILED`, `bundlewrap.items.Item.STATUS_SKIPPED`, `bundlewrap.items.Item.STATUS_OK`, or `bundlewrap.items.Item.STATUS_FIXED`.

`status_before` An instance of `bundlewrap.items.ItemStatus`.

`status_after` See `status_before`.

---

**`lock_add(repo, node, lock_id, items, expiry, comment, **kwargs)`**

Called each time a soft lock is added to a node.

`repo` The current repository (instance of `bundlewrap.repo.Repository`).

`node` The current node (instance of `bundlewrap.node.Node`).

`lock_id` The random ID of the lock.

`items` List of item selector strings.

`expiry` UNIX timestamp of lock expiry time (int).

`comment` As entered by user.

---

**`lock_remove(repo, node, lock_id, **kwargs)`**

Called each time a soft lock is removed from a node.

`repo` The current repository (instance of `bundlewrap.repo.Repository`).

`node` The current node (instance of `bundlewrap.node.Node`).

`lock_id` The random ID of the lock.

---

**`lock_show(repo, node, lock_info, **kwargs)`**

Called each time `bw lock show` finds a lock on a node.

`repo` The current repository (instance of `bundlewrap.repo.Repository`).

`node` The current node (instance of `bundlewrap.node.Node`).

`lock_info` A dict contain the lock details.

---

**`node_apply_start(repo, node, interactive=False, **kwargs)`**

Called each time a `bw apply` command reaches a new node.

`repo` The current repository (instance of `bundlewrap.repo.Repository`).

`node` The current node (instance of `bundlewrap.node.Node`).

`interactive` `True` if this is an interactive apply run.

To skip a node:

```
from bundlewrap.exceptions import SkipNode
raise SkipNode("reason goes here")
```

---

**`node_apply_end(repo, node, duration=None, interactive=False, result=None, **kwargs)`**

Called each time a `bw apply` command finishes processing a node.

`repo` The current repository (instance of `bundlewrap.repo.Repository`).

`node` The current node (instance of `bundlewrap.node.Node`).

`duration` How long the apply took (timedelta).

`interactive` `True` if this was an interactive apply run.

`result` An instance of `bundlewrap.node.ApplyResult`.

---

**`node_run_start(repo, node, command, **kwargs)`**

Called each time a `bw run` command reaches a new node.

`repo` The current repository (instance of `bundlewrap.repo.Repository`).

`node` The current node (instance of `bundlewrap.node.Node`).

`command` The command that will be run on the node.

To skip a node:

```
from bundlewrap.exceptions import SkipNode
raise SkipNode("reason goes here")
```

---

**`node_run_end(repo, node, command, duration=None, return_code=None, stdout="", stderr="", **kwargs)`**

Called each time a `bw run` command finishes on a node.

`repo` The current repository (instance of `bundlewrap.repo.Repository`).

`node` The current node (instance of `bundlewrap.node.Node`).

`command` The command that was run on the node.

`duration` How long it took to run the command (timedelta).

`return_code` Return code of the remote command.

`stdout` The captured stdout stream of the remote command.

`stderr` The captured stderr stream of the remote command.

---

**`run_start(repo, target, nodes, command, **kwargs)`**

Called each time a `bw run` command starts.

`repo` The current repository (instance of `bundlewrap.repo.Repository`).

`target` The group or node name you gave on the command line.

`nodes` A list of node objects affected (list of `bundlewrap.node.Node` instances).

`command` The command that will be run on the node.

---

**`run_end(repo, target, nodes, command, duration=None, **kwargs)`**

Called each time a `bw run` command finishes.

`repo` The current repository (instance of `bundlewrap.repo.Repository`).

`target` The group or node name you gave on the command line.

`nodes` A list of node objects affected (list of `bundlewrap.node.Node` instances).

`command` The command that was run.

`duration` How long it took to run the command on all nodes (timedelta).

---

**`test(repo, **kwargs)`**

Called at the end of a full `bw test`.

`repo` The current repository (instance of `bundlewrap.repo.Repository`).

---

**`test_node(repo, node, **kwargs)`**

Called during `bw test` for each node.

`repo` The current repository (instance of `bundlewrap.repo.Repository`).

`node` The current node (instance of `bundlewrap.node.Node`).
