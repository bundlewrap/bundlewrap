from datetime import datetime

from ..concurrency import WorkerPool
from ..utils import LOG
from ..utils.cmdline import get_target_nodes
from ..utils.text import green, red, white, yellow
from ..utils.text import mark_for_translation as _


def format_node_result(result):
    output = []
    output.append(("{} correct").format(result.correct))

    if result.fixed:
        output.append(green(_("{} fixed").format(result.fixed)))
    else:
        output.append(_("{} fixed").format(result.fixed))

    if result.aborted:
        output.append(yellow(_("{} aborted").format(result.aborted)))
    else:
        output.append(_("{} aborted").format(result.aborted))

    if result.unfixable:
        output.append(red(_("{} unfixable").format(result.unfixable)))
    else:
        output.append(_("{} unfixable").format(result.unfixable))

    if result.failed:
        output.append(red(_("{} failed").format(result.failed)))
    else:
        output.append(_("{} failed").format(result.failed))

    return ", ".join(output)


def bw_apply(repo, args):
    target_nodes = get_target_nodes(repo, args.target)
    worker_count = 1 if args.interactive else args.node_workers
    with WorkerPool(workers=worker_count) as worker_pool:
        results = {}
        while (
                target_nodes or
                worker_pool.busy_count > 0 or
                worker_pool.reapable_count > 0
        ):
            while target_nodes:
                worker = worker_pool.get_idle_worker(block=False)
                if worker is None:
                    break
                node = target_nodes.pop()
                start_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                if args.interactive:
                    yield _("\n{}: run started at {}").format(
                        white(node.name, bold=True),
                        start_time,
                    )
                else:
                    LOG.info(_("{}: run started at {}").format(
                        node.name,
                        start_time,
                    ))

                worker.start_task(
                    node.apply,
                    id=node.name,
                    kwargs={
                        'interactive': args.interactive,
                    },
                )
            while worker_pool.reapable_count > 0:
                worker = worker_pool.get_reapable_worker()
                node_name = worker.id
                results[node_name] = worker.reap()
                if args.interactive:
                    yield _("\n  {}: run completed after {}s").format(
                        white(node_name, bold=True),
                        results[node_name].duration.total_seconds(),
                    )
                    yield "  " + format_node_result(results[node_name]) + "\n"
                else:
                    LOG.info(_("{}: run completed after {}s").format(
                        node_name,
                        results[node_name].duration.total_seconds(),
                    ))
                    LOG.info(_("{}: stats: {}").format(
                        node_name,
                        format_node_result(results[node_name]),
                    ))
            if (
                worker_pool.busy_count > 0 and
                not target_nodes and
                not worker_pool.reapable_count
            ):
                worker_pool.wait()
