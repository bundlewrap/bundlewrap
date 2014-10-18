# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from copy import copy
from sys import exit

from ..concurrency import WorkerPool
from ..exceptions import WorkerException
from ..utils.cmdline import get_target_nodes
from ..utils.text import red


def bw_test(repo, args):
    if args['target']:
        pending_nodes = get_target_nodes(repo, args['target'])
    else:
        pending_nodes = copy(list(repo.nodes))
    with WorkerPool(workers=args['node_workers']) as worker_pool:
        while worker_pool.keep_running():
            try:
                msg = worker_pool.get_event()
            except WorkerException as e:
                msg = "{} {}\n".format(
                    red("✘"),
                    e.task_id,
                )
                yield msg
                yield e.traceback
                exit(1)
                break  # for testing, when exit() is patched
            if msg['msg'] == 'REQUEST_WORK':
                if pending_nodes:
                    node = pending_nodes.pop()
                    worker_pool.start_task(
                        msg['wid'],
                        node.test,
                        task_id=node.name,
                        kwargs={
                            'workers': args['item_workers'],
                        },
                    )
                else:
                    worker_pool.quit(msg['wid'])
