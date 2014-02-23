# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from ..concurrency import WorkerPool
from ..exceptions import WorkerException
from ..utils.cmdline import get_target_nodes
from ..utils.text import error_summary, red


def bw_verify(repo, args):
    errors = []
    target_nodes = get_target_nodes(repo, args.target)
    with WorkerPool(workers=args.node_workers) as worker_pool:
        while worker_pool.keep_running():
            try:
                msg = worker_pool.get_event()
            except WorkerException as e:
                msg = "{} {}: {}".format(
                    red("!"),
                    e.task_id,
                    e.wrapped_exception,
                )
                if args.debug:
                    yield e.traceback
                yield msg
                errors.append(msg)
                continue
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

    error_summary(errors)
