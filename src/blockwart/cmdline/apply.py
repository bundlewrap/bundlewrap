from ..concurrency import WorkerPool
from ..exceptions import UsageException
from ..utils import LOG, mark_for_translation as _


def _get_target_list(repo, groups, nodes):
    target_nodes = []
    if groups:
        for group_name in groups.split(","):
            group_name = group_name.strip()
            group = repo.get_group(group_name)
            target_nodes += list(group.nodes)
    if nodes:
        for node_name in nodes.split(","):
            node_name = node_name.strip()
            node = repo.get_node(node_name)
            target_nodes.append(node)
    if not target_nodes:
        raise UsageException(_("specify at least one node or group"))
    target_nodes = list(set(target_nodes))
    target_nodes.sort()
    return target_nodes


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
    target_nodes = _get_target_list(repo, args.groups, args.nodes)
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
