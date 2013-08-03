from ..concurrency import WorkerPool
from ..utils import LOG
from ..utils.cmdline import get_target_nodes


def format_node_result(args, node_name, result):
    return ("{}: {} correct, {} fixed, {} aborted, {} unfixable, "
            "{} failed".format(
                node_name,
                result.correct,
                result.fixed,
                result.aborted,
                result.unfixable,
                result.failed,
            ))


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
                LOG.info(format_node_result(args, node_name,
                                            results[node_name]))
            if (
                worker_pool.busy_count > 0 and
                not target_nodes and
                not worker_pool.reapable_count
            ):
                worker_pool.wait()
