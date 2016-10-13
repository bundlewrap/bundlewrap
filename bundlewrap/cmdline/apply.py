# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from datetime import datetime
from sys import exit

from ..concurrency import WorkerPool
from ..utils.cmdline import get_target_nodes
from ..utils.text import bold
from ..utils.text import error_summary, mark_for_translation as _
from ..utils.ui import io


def bw_apply(repo, args):
    errors = []
    target_nodes = get_target_nodes(repo, args['target'], adhoc_nodes=args['adhoc_nodes'])
    pending_nodes = target_nodes[:]

    repo.hooks.apply_start(
        repo,
        args['target'],
        target_nodes,
        interactive=args['interactive'],
    )

    start_time = datetime.now()

    def tasks_available():
        return bool(pending_nodes)

    def next_task():
        node = pending_nodes.pop()
        return {
            'target': node.apply,
            'task_id': node.name,
            'kwargs': {
                'autoskip_selector': args['autoskip'],
                'force': args['force'],
                'interactive': args['interactive'],
                'workers': args['item_workers'],
                'profiling': args['profiling'],
            },
        }

    def handle_result(task_id, return_value, duration):
        if (
            return_value is not None and  # node skipped because it had no items
            args['profiling']
        ):
            total_time = 0.0
            io.stdout(_("  {}").format(bold(task_id)))
            io.stdout(_("  {} BEGIN PROFILING DATA "
                        "(most expensive items first)").format(bold(task_id)))
            io.stdout(_("  {}    seconds   item").format(bold(task_id)))
            for time_elapsed, item_id in return_value.profiling_info:
                io.stdout("  {} {:10.3f}   {}".format(
                    bold(task_id),
                    time_elapsed.total_seconds(),
                    item_id,
                ))
                total_time += time_elapsed.total_seconds()
            io.stdout(_("  {} {:10.3f}   (total)").format(bold(task_id), total_time))
            io.stdout(_("  {} END PROFILING DATA").format(bold(task_id)))
            io.stdout(_("  {}").format(bold(task_id)))

    def handle_exception(task_id, exception, traceback):
        msg = "{}: {}".format(task_id, exception)
        io.stderr(traceback)
        io.stderr(repr(exception))
        io.stderr(msg)
        errors.append(msg)

    worker_pool = WorkerPool(
        tasks_available,
        next_task,
        handle_result=handle_result,
        handle_exception=handle_exception,
        pool_id="apply",
        workers=args['node_workers'],
    )
    worker_pool.run()

    error_summary(errors)

    repo.hooks.apply_end(
        repo,
        args['target'],
        target_nodes,
        duration=datetime.now() - start_time,
    )

    exit(1 if errors else 0)
