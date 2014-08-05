from datetime import datetime

from ..concurrency import WorkerPool
from ..exceptions import WorkerException
from ..utils import LOG
from ..utils.cmdline import get_target_nodes
from ..utils.text import bold, green, red, yellow
from ..utils.text import error_summary, mark_for_translation as _


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
    target_nodes = get_target_nodes(repo, args.target)

    repo.hooks.apply_start(
        repo,
        args.target,
        target_nodes,
        interactive=args.interactive,
    )

    start_time = datetime.now()

    worker_count = 1 if args.interactive else args.node_workers
    with WorkerPool(workers=worker_count) as worker_pool:
        results = {}
        while worker_pool.keep_running():
            try:
                msg = worker_pool.get_event()
            except WorkerException as e:
                msg = "{} {}".format(red("!"), e.wrapped_exception)
                if args.debug:
                    yield e.traceback
                if not args.interactive:
                    msg = "{}: {}".format(e.task_id, msg)
                yield msg
                errors.append(msg)
                continue
            if msg['msg'] == 'REQUEST_WORK':
                if target_nodes:
                    node = target_nodes.pop()
                    node_start_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

                    if args.interactive:
                        yield _("\n{}: run started at {}").format(
                            bold(node.name),
                            node_start_time,
                        )
                    else:
                        LOG.info(_("{}: run started at {}").format(
                            node.name,
                            node_start_time,
                        ))

                    worker_pool.start_task(
                        msg['wid'],
                        node.apply,
                        task_id=node.name,
                        kwargs={
                            'force': args.force,
                            'interactive': args.interactive,
                            'workers': args.item_workers,
                            'profiling': args.profiling,
                        },
                    )
                else:
                    worker_pool.quit(msg['wid'])
            elif msg['msg'] == 'FINISHED_WORK':
                node_name = msg['task_id']
                results[node_name] = msg['return_value']

                if args.profiling:
                    total_time = 0.0
                    yield _("{}: BEGIN PROFILING DATA (most expensive items first)").format(node_name)
                    yield _("{}:    seconds   item").format(node_name)
                    for time_elapsed, item_id in results[node_name].profiling_info:
                        yield "{}: {:10.3f}   {}".format(node_name, time_elapsed.total_seconds(), item_id)
                        total_time += time_elapsed.total_seconds()
                    yield _("{}: {:10.3f}   (total)").format(node_name, total_time)
                    yield _("{}: END PROFILING DATA").format(node_name)

                if args.interactive:
                    yield _("\n{node}: run completed after {time}s ({stats})\n").format(
                        node=bold(node_name),
                        time=results[node_name].duration.total_seconds(),
                        stats=format_node_result(results[node_name]),
                    )
                else:
                    LOG.info(_("{node}: run completed after {time}s").format(
                        node=node_name,
                        time=results[node_name].duration.total_seconds(),
                    ))
                    LOG.info(_("{node}: stats: {stats}").format(
                        node=node_name,
                        stats=format_node_result(results[node_name]),
                    ))

    error_summary(errors)

    repo.hooks.apply_end(
        repo,
        args.target,
        target_nodes,
        duration=datetime.now() - start_time,
    )
