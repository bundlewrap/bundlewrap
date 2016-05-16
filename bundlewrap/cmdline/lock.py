# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from datetime import datetime

from ..concurrency import WorkerPool
from ..lock import softlock_add, softlock_list, softlock_remove
from ..utils.cmdline import get_target_nodes
from ..utils.text import blue, bold, cyan, error_summary, green, mark_for_translation as _
from ..utils.ui import io


def bw_lock_add(repo, args):
    errors = []
    target_nodes = get_target_nodes(repo, args['target'])
    pending_nodes = target_nodes[:]

    def tasks_available():
        return bool(pending_nodes)

    def next_task():
        node = pending_nodes.pop()
        return {
            'target': softlock_add,
            'task_id': node.name,
            'args': (node,),
            'kwargs': {
                'comment': args['comment'],
                'expiry': args['expiry'],
            },
        }

    def handle_result(task_id, return_value, duration):
        io.stdout(_("{x} {node}  locked with ID {id} (expires in {exp})").format(
            x=green("✓"),
            node=bold(task_id),
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
    node = repo.get_node(args['target'])
    lock = args['lock_id'].upper()
    softlock_remove(node, lock)
    io.stdout(_("{x} {node}  lock {lock} removed").format(
        x=green("✓"),
        node=bold(node.name),
        lock=lock,
    ))


def bw_lock_show(repo, args):
    node = repo.get_node(args['target'])
    locks = softlock_list(node)

    if not locks:
        io.stdout(_("{x} {node}  no soft locks present").format(
            x=green("✓"),
            node=bold(node.name),
        ))
        return

    for lock in locks:
        lock['formatted_date'] = \
            datetime.fromtimestamp(lock['date']).strftime("%Y-%m-%d %H:%M:%S")
        lock['formatted_expiry'] = \
            datetime.fromtimestamp(lock['expiry']).strftime("%Y-%m-%d %H:%M:%S")
        lock['formatted_ops'] = ", ".join(sorted(lock['ops']))

    headers = (
        ('id', _("ID")),
        ('formatted_date', _("Created")),
        ('formatted_expiry', _("Expires")),
        ('user', _("User")),
        ('formatted_ops', _("Operations")),
        ('comment', _("Comment")),
    )
    lengths = {}
    headline = "{x} {node}  ".format(
        x=blue("i"),
        node=bold(node.name),
    )

    for column, title in headers:
        lengths[column] = len(title)
        for lock in locks:
            lengths[column] = max(lengths[column], len(lock[column]))
        headline += bold(title.ljust(lengths[column] + 2))

    io.stdout(headline.rstrip())
    for lock in locks:
        line = "{x} {node}  ".format(
            x=cyan("›"),
            node=bold(node.name),
        )
        for column, title in headers:
            line += lock[column].ljust(lengths[column] + 2)
        io.stdout(line.rstrip())
