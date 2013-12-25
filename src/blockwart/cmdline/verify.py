# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from ..concurrency import WorkerPool
from ..utils.cmdline import get_target_nodes


def bw_verify(repo, args):
    target_nodes = get_target_nodes(repo, args.target)
    with WorkerPool(workers=args.node_workers) as worker_pool:
        while worker_pool.keep_running():
            msg = worker_pool.get_event()
            if msg['msg'] == 'REQUEST_WORK':
                if target_nodes:
                    node = target_nodes.pop()
                    worker_pool.start_task(
                        msg['wid'],
                        node.verify,
                        task_id=node.name,
                        kwargs={
                            'workers': args.item_workers,
                        },
                    )
                else:
                    worker_pool.quit(msg['wid'])
            # Nothing to do for the 'FINISHED_WORK' message.
