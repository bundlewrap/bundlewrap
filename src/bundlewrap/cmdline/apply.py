# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from datetime import datetime

from ..concurrency import WorkerPool
from ..exceptions import WorkerException
from ..utils.cmdline import get_target_nodes
from ..utils.text import bold, blue, green, red, yellow
from ..utils.text import error_summary, mark_for_translation as _
from ..utils.ui import io


def format_node_result(result):
    output = []
    output.append(("{count} OK").format(count=result.correct))

    if result.fixed:
        output.append(green(_("{count} fixed").format(count=result.fixed)))
    else:
        output.append(_("{count} fixed").format(count=result.fixed))

    if result.skipped:
        output.append(yellow(_("{count} skipped").format(count=result.skipped)))
    else:
        output.append(_("{count} skipped").format(count=result.skipped))

    if result.failed:
        output.append(red(_("{count} failed").format(count=result.failed)))
    else:
        output.append(_("{count} failed").format(count=result.failed))

    return ", ".join(output)


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

    worker_count = 1 if args['interactive'] else args['node_workers']
    with WorkerPool(workers=worker_count) as worker_pool:
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
                    node_start_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

                    io.stdout(_("{x} {node} run started at {time}").format(
                        node=bold(node.name),
                        time=node_start_time,
                        x=blue("i"),
                    ))

                    worker_pool.start_task(
                        msg['wid'],
                        node.apply,
                        task_id=node.name,
                        kwargs={
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

                io.stdout(_("{x} {node} run completed after {time}s").format(
                    node=bold(node_name),
                    time=results[node_name].duration.total_seconds(),
                    x=blue("i"),
                ))
                io.stdout(_("{x} {node} stats: {stats}").format(
                    node=bold(node_name),
                    stats=format_node_result(results[node_name]),
                    x=blue("i"),
                ))

    error_summary(errors)

    repo.hooks.apply_end(
        repo,
        args['target'],
        target_nodes,
        duration=datetime.now() - start_time,
    )
