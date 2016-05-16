# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from ..concurrency import WorkerPool
from ..lock import softlock_add
from ..utils.cmdline import get_target_nodes
from ..utils.text import bold, error_summary, green, mark_for_translation as _
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
        }

    def handle_result(task_id, return_value, duration):
        io.stdout(_("{x} {node}  locked").format(
            x=green("✓"),
            node=bold(task_id),
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
