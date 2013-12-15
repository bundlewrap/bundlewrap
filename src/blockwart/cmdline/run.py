# -*- coding: utf-8 -*-
from __future__ import unicode_literals

import sys

from datetime import datetime

from ..concurrency import WorkerPool
from ..utils import LOG
from ..utils.cmdline import get_target_nodes
from ..utils.text import mark_for_translation as _
from ..utils.text import green, red
from ..utils.ui import LineBuffer


def run_on_node(node, command, may_fail, sudo, interactive):
    if interactive:
        stdout = sys.stdout
        stderr = sys.stderr
    else:
        stdout = LineBuffer(LOG.info)
        stderr = LineBuffer(LOG.error)

    start = datetime.now()
    result = node.run(
        command,
        may_fail=may_fail,
        stdout=stdout,
        stderr=stderr,
        sudo=sudo,
        pty=interactive,
    )
    end = datetime.now()
    duration = end - start
    if result.return_code == 0:
        yield "[{}] {} {}".format(
            node.name,
            green("✓"),
            _("completed successfully after {}s").format(
                duration.total_seconds(),
            ),
        )
    else:
        yield "[{}] {} {}".format(
            node.name,
            red("✘"),
            _("failed after {}s (return code {})").format(
                duration.total_seconds(),
                result.return_code,
            ),
        )


def bw_run(repo, args):
    target_nodes = get_target_nodes(repo, args.target)
    with WorkerPool(workers=args.node_workers) as worker_pool:
        while worker_pool.keep_running():
            msg = worker_pool.get_event()
            if msg['msg'] == 'REQUEST_WORK':
                if target_nodes:
                    node = target_nodes.pop()
                    worker_pool.start_task(
                        msg['wid'],
                        run_on_node,
                        task_id=node.name,
                        args=(
                            node,
                            args.command,
                            args.may_fail,
                            args.sudo,
                            args.node_workers == 1,
                        ),
                    )
                else:
                    worker_pool.quit(msg['wid'])
            elif msg['msg'] == 'FINISHED_WORK':
                for line in msg['return_value']:
                    yield line
