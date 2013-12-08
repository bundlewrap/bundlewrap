# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from ..concurrency import WorkerPool
from ..utils.cmdline import get_target_nodes


def bw_verify(repo, args):
    target_nodes = get_target_nodes(repo, args.target)
    worker_count = args.node_workers
    with WorkerPool(workers=worker_count) as worker_pool:
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
                    node.verify,
                    id=node.name,
                    kwargs={
                        'workers': args.item_workers,
                    },
                )
            while worker_pool.reapable_count > 0:
                worker = worker_pool.get_reapable_worker()
                worker.reap()

            if (
                worker_pool.busy_count > 0 and
                not target_nodes and
                not worker_pool.reapable_count
            ):
                worker_pool.wait()
