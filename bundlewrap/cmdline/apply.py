# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from datetime import datetime

from ..concurrency import WorkerPool
from ..exceptions import WorkerException
from ..utils.cmdline import get_target_nodes
from ..utils.text import bold, red
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
        results = {}
        while worker_pool.keep_running():
            try:
                msg = worker_pool.get_event()
            except WorkerException as e:
                msg = "{} {}".format(red("!"), e.wrapped_exception)
                if args['debug']:
                    yield e.traceback
                if not args['interactive']:
                    msg = "{}: {}".format(e.task_id, msg)
                yield msg
                errors.append(msg)
                continue
            if msg['msg'] == 'REQUEST_WORK':
                if pending_nodes:
                    node = pending_nodes.pop()

                    worker_pool.start_task(
                        msg['wid'],
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
                else:
                    worker_pool.quit(msg['wid'])
            elif msg['msg'] == 'FINISHED_WORK':
                node_name = msg['task_id']
                if msg['return_value'] is not None:  # node skipped because it had no items
                    results[node_name] = msg['return_value']

                    if args['profiling']:
                        total_time = 0.0
                        yield _("  {}").format(bold(node_name))
                        yield _("  {} BEGIN PROFILING DATA "
                                "(most expensive items first)").format(bold(node_name))
                        yield _("  {}    seconds   item").format(bold(node_name))
                        for time_elapsed, item_id in results[node_name].profiling_info:
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
