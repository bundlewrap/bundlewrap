# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from datetime import datetime

from ..concurrency import WorkerPool
from ..exceptions import WorkerException
from ..utils.cmdline import get_target_nodes
from ..utils.text import bold
from ..utils.text import error_summary, mark_for_translation as _


def bw_apply(repo, args):
    errors = []
    target_nodes = get_target_nodes(repo, args['target'])
    pending_nodes = target_nodes[:]

    repo.hooks.apply_start(
        repo,
        args['target'],
        target_nodes,
        interactive=args['interactive'],
    )

    start_time = datetime.now()

    with WorkerPool(workers=args['node_workers']) as worker_pool:
        while pending_nodes or worker_pool.workers_are_running:
            while pending_nodes and worker_pool.workers_are_available:
                node = pending_nodes.pop()
                worker_pool.start_task(
                    node.apply,
                    task_id=node.name,
                    kwargs={
                        'autoskip_selector': args['autoskip'],
                        'force': args['force'],
                        'interactive': args['interactive'],
                        'workers': args['item_workers'],
                        'profiling': args['profiling'],
                    },
                )

            try:
                result = worker_pool.get_result()
            except WorkerException as exc:
                msg = "{}: {}".format(
                    exc.kwargs['task_id'],
                    exc.wrapped_exception,
                )
                if args['debug']:
                    yield exc.traceback
                    yield repr(exc)
                yield msg
                errors.append(msg)
            else:
                node_name = result['task_id']
                if (
                    result['return_value'] is not None and  # node skipped because it had no items
                    args['profiling']
                ):
                    total_time = 0.0
                    yield _("  {}").format(bold(node_name))
                    yield _("  {} BEGIN PROFILING DATA "
                            "(most expensive items first)").format(bold(node_name))
                    yield _("  {}    seconds   item").format(bold(node_name))
                    for time_elapsed, item_id in result['return_value'].profiling_info:
                        yield "  {} {:10.3f}   {}".format(
                            bold(node_name),
                            time_elapsed.total_seconds(),
                            item_id,
                        )
                        total_time += time_elapsed.total_seconds()
                    yield _("  {} {:10.3f}   (total)").format(bold(node_name), total_time)
                    yield _("  {} END PROFILING DATA").format(bold(node_name))
                    yield _("  {}").format(bold(node_name))

    error_summary(errors)

    repo.hooks.apply_end(
        repo,
        args['target'],
        target_nodes,
        duration=datetime.now() - start_time,
    )

    yield 1 if errors else 0
