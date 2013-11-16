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


def run_on_node(node, command, may_fail, sudo, verbose, interactive):
    if interactive:
        stdout = sys.stdout
        stderr = sys.stderr
    else:
        stdout = LineBuffer(LOG.info)
        stderr = LineBuffer(LOG.info)

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
        if not verbose and not interactive:
            # show output of failed command if not already shown by -v
            for stream in (result.stdout, result.stderr):
                for line in stream.splitlines():
                    yield line
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
                    run_on_node,
                    id=node.name,
                    args=(
                        node,
                        args.command,
                        args.may_fail,
                        args.sudo,
                        args.verbose,
                        args.node_workers == 1,
                    ),
                )
            while worker_pool.reapable_count > 0:
                worker = worker_pool.get_reapable_worker()
                for line in worker.reap():
                    yield line
            if (
                worker_pool.busy_count > 0 and
                not target_nodes and
                not worker_pool.reapable_count
            ):
                worker_pool.wait()
