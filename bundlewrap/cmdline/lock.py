from sys import exit

from ..concurrency import WorkerPool
from ..lock import (
    softlock_add_and_warn_for_others,
    softlock_list,
    softlock_remove,
    softlocks_to_table,
)
from ..utils.cmdline import get_target_nodes
from ..utils.text import (
    bold,
    error_summary,
    green,
    mark_for_translation as _,
    randstr,
    red,
    yellow,
)
from ..utils.ui import io, page_lines


def remove_dummy_nodes(targets):
    _targets = []
    for node in targets:
        if node.dummy:
            io.stdout(_("{x} {node}  is a dummy node").format(node=bold(node.name), x=yellow("»")))
        else:
            _targets.append(node)
    return _targets


def remove_lock_if_present(node, lock_id):
    for lock in softlock_list(node):
        if lock['id'] == lock_id:
            softlock_remove(node, lock_id)
            return True
    return False


def bw_lock_add(repo, args):
    errors = []
    target_nodes = get_target_nodes(repo, args['targets'], args['node_workers'])
    target_nodes = remove_dummy_nodes(target_nodes)
    if not target_nodes:
        return

    pending_nodes = target_nodes[:]
    max_node_name_length = max([len(node.name) for node in target_nodes])
    lock_id = randstr(length=4).upper()
    io.progress_set_total(len(pending_nodes))

    def tasks_available():
        return bool(pending_nodes)

    def next_task():
        node = pending_nodes.pop()
        return {
            'target': softlock_add_and_warn_for_others,
            'task_id': node.name,
            'args': (node, lock_id),
            'kwargs': {
                'comment': args['comment'],
                'expiry': args['expiry'],
                'item_selectors': args['items'],
            },
        }

    def handle_result(task_id, return_value, duration):
        io.progress_advance()
        io.stdout(_("{x} {node}  locked with ID {id} (expires in {exp})").format(
            x=green("✓"),
            node=bold(task_id.ljust(max_node_name_length)),
            id=return_value,
            exp=args['expiry'],
        ))

    def handle_exception(task_id, exception, traceback):
        msg = "{}: {}".format(task_id, exception)
        io.stderr(traceback)
        io.stderr(repr(exception))
        io.stderr(msg)
        errors.append(msg)

    worker_pool = WorkerPool(
        tasks_available,
        next_task,
        handle_exception=handle_exception,
        handle_result=handle_result,
        pool_id="lock",
        workers=args['node_workers'],
    )
    worker_pool.run()

    error_summary(errors)


def bw_lock_remove(repo, args):
    errors = []
    target_nodes = get_target_nodes(repo, args['targets'], args['node_workers'])
    target_nodes = remove_dummy_nodes(target_nodes)
    if not target_nodes:
        return

    pending_nodes = target_nodes[:]
    max_node_name_length = max([len(node.name) for node in target_nodes])
    io.progress_set_total(len(pending_nodes))

    def tasks_available():
        return bool(pending_nodes)

    def next_task():
        node = pending_nodes.pop()
        return {
            'target': remove_lock_if_present,
            'task_id': node.name,
            'args': (node, args['lock_id'].upper()),
        }

    def handle_result(task_id, return_value, duration):
        io.progress_advance()
        if return_value is True:
            io.stdout(_("{x} {node}  lock {id} removed").format(
                x=green("✓"),
                node=bold(task_id.ljust(max_node_name_length)),
                id=args['lock_id'].upper(),
            ))
        else:
            io.stderr(_(
                "{x} {node}  has no lock with ID {id}"
            ).format(
                x=red("!"),
                node=bold(task_id.ljust(max_node_name_length)),
                id=args['lock_id'].upper(),
            ))

    def handle_exception(task_id, exception, traceback):
        msg = "{}: {}".format(task_id, exception)
        io.stderr(traceback)
        io.stderr(repr(exception))
        io.stderr(msg)
        errors.append(msg)

    worker_pool = WorkerPool(
        tasks_available,
        next_task,
        handle_exception=handle_exception,
        handle_result=handle_result,
        pool_id="lock_remove",
        workers=args['node_workers'],
    )
    worker_pool.run()

    error_summary(errors)


def bw_lock_show(repo, args):
    errors = []
    target_nodes = get_target_nodes(repo, args['targets'], args['node_workers'])
    target_nodes = remove_dummy_nodes(target_nodes)
    if not target_nodes:
        return

    pending_nodes = target_nodes[:]
    locks_on_node = {}

    def tasks_available():
        return bool(pending_nodes)

    def next_task():
        node = pending_nodes.pop()
        return {
            'target': softlock_list,
            'task_id': node.name,
            'args': (node,),
        }

    def handle_result(task_id, return_value, duration):
        locks_on_node[task_id] = return_value
        repo.hooks.lock_show(repo, repo.get_node(task_id), return_value)

    def handle_exception(task_id, exception, traceback):
        msg = "{}: {}".format(task_id, exception)
        io.stderr(traceback)
        io.stderr(repr(exception))
        io.stderr(msg)
        errors.append(msg)

    worker_pool = WorkerPool(
        tasks_available,
        next_task,
        handle_exception=handle_exception,
        handle_result=handle_result,
        pool_id="lock_show",
        workers=args['node_workers'],
    )
    worker_pool.run()

    output, some_selected_items_locked = softlocks_to_table(
        locks_on_node,
        items=args['items'],
        repo=repo,
        hide_nodes_without_locks=args['hide_not_locked'],
    )
    page_lines(output)
    error_summary(errors)

    exit(47 if some_selected_items_locked else 0)
