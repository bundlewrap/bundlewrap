# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from ..concurrency import WorkerPool
from ..lock import softlock_add, softlock_list, softlock_remove
from ..utils.cmdline import get_target_nodes
from ..utils.text import blue, bold, cyan, error_summary, green, mark_for_translation as _, \
    randstr
from ..utils.time import format_timestamp
from ..utils.ui import io


def bw_lock_add(repo, args):
    errors = []
    target_nodes = get_target_nodes(repo, args['target'], adhoc_nodes=args['adhoc_nodes'])
    pending_nodes = target_nodes[:]
    max_node_name_length = max([len(node.name) for node in target_nodes])
    lock_id = randstr(length=4).upper()

    def tasks_available():
        return bool(pending_nodes)

    def next_task():
        node = pending_nodes.pop()
        return {
            'target': softlock_add,
            'task_id': node.name,
            'args': (node, lock_id),
            'kwargs': {
                'comment': args['comment'],
                'expiry': args['expiry'],
                'item_selectors': args['items'].split(","),
            },
        }

    def handle_result(task_id, return_value, duration):
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
    target_nodes = get_target_nodes(repo, args['target'], adhoc_nodes=args['adhoc_nodes'])
    pending_nodes = target_nodes[:]
    max_node_name_length = max([len(node.name) for node in target_nodes])

    def tasks_available():
        return bool(pending_nodes)

    def next_task():
        node = pending_nodes.pop()
        return {
            'target': softlock_remove,
            'task_id': node.name,
            'args': (node, args['lock_id'].upper()),
        }

    def handle_result(task_id, return_value, duration):
        io.stdout(_("{x} {node}  lock {id} removed").format(
            x=green("✓"),
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
    target_nodes = get_target_nodes(repo, args['target'], adhoc_nodes=args['adhoc_nodes'])
    pending_nodes = target_nodes[:]
    max_node_name_length = max([len(node.name) for node in target_nodes])
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

    if errors:
        error_summary(errors)
        return

    headers = (
        ('id', _("ID")),
        ('formatted_date', _("Created")),
        ('formatted_expiry', _("Expires")),
        ('user', _("User")),
        ('items', _("Items")),
        ('comment', _("Comment")),
    )

    locked_nodes = 0
    for node_name, locks in locks_on_node.items():
        if locks:
            locked_nodes += 1

    previous_node_was_unlocked = False
    for node_name, locks in sorted(locks_on_node.items()):
        if not locks:
            io.stdout(_("{x} {node}  no soft locks present").format(
                x=green("✓"),
                node=bold(node_name.ljust(max_node_name_length)),
            ))
            previous_node_was_unlocked = True

    output_counter = 0
    for node_name, locks in sorted(locks_on_node.items()):
        if locks:
            # Unlocked nodes are printed without empty lines in
            # between them. Locked nodes can produce lengthy output,
            # though, so we add empty lines.
            if (
                previous_node_was_unlocked or (
                    output_counter > 0 and output_counter < locked_nodes
                )
            ):
                previous_node_was_unlocked = False
                io.stdout('')

            for lock in locks:
                lock['formatted_date'] = format_timestamp(lock['date'])
                lock['formatted_expiry'] = format_timestamp(lock['expiry'])

            lengths = {}
            headline = "{x} {node}  ".format(
                x=blue("i"),
                node=bold(node_name.ljust(max_node_name_length)),
            )

            for column, title in headers:
                lengths[column] = len(title)
                for lock in locks:
                    if column == 'items':
                        length = max([len(selector) for selector in lock[column]])
                    else:
                        length = len(lock[column])
                    lengths[column] = max(lengths[column], length)
                headline += bold(title.ljust(lengths[column] + 2))

            io.stdout(headline.rstrip())
            for lock in locks:
                for lineno, item_selectors in enumerate(lock['items']):
                    line = "{x} {node}  ".format(
                        x=cyan("›"),
                        node=bold(node_name.ljust(max_node_name_length)),
                    )
                    for column, title in headers:
                        if column == 'items':
                            line += lock[column][lineno].ljust(lengths[column] + 2)
                        elif lineno == 0:
                            line += lock[column].ljust(lengths[column] + 2)
                        else:
                            line += " " * (lengths[column] + 2)
                    io.stdout(line.rstrip())

            output_counter += 1
