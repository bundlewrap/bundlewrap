# -*- coding: utf-8 -*-
from __future__ import unicode_literals

import sys

from datetime import datetime

from ..concurrency import WorkerPool
from ..exceptions import WorkerException
from ..utils import LOG
from ..utils.cmdline import get_target_nodes
from ..utils.text import mark_for_translation as _
from ..utils.text import error_summary, green, red
from ..utils.ui import LineBuffer


def run_on_node(node, command, may_fail, sudo, interactive):
    if interactive:
        stdout = sys.stdout
        stderr = sys.stderr
    else:
        stdout = LineBuffer(LOG.info)
        stderr = LineBuffer(LOG.error)

    node.repo.hooks.node_run_start(
        node.repo,
        node,
        command,
    )

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

    node.repo.hooks.node_run_end(
        node.repo,
        node,
        command,
        duration=duration,
        return_code=result.return_code,
        stdout=result.stdout,
        stderr=result.stderr,
    )

    if result.return_code == 0:
        yield "[{}] {} {}".format(
            node.name,
            green("✓"),
            _("completed successfully after {time}s").format(
                time=duration.total_seconds(),
            ),
        )
    else:
        yield "[{}] {} {}".format(
            node.name,
            red("✘"),
            _("failed after {time}s (return code {rcode})").format(
                rcode=result.return_code,
                time=duration.total_seconds(),
            ),
        )


def bw_run(repo, args):
    errors = []
    target_nodes = get_target_nodes(repo, args.target)

    repo.hooks.run_start(
        repo,
        args.target,
        target_nodes,
        args.command,
    )
    start_time = datetime.now()

    with WorkerPool(workers=args.node_workers) as worker_pool:
        while worker_pool.keep_running():
            try:
                msg = worker_pool.get_event()
            except WorkerException as e:
                msg = "[{}] {} {}".format(
                    e.task_id,
                    red("!"),
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

    error_summary(errors)

    repo.hooks.run_end(
        repo,
        args.target,
        target_nodes,
        args.command,
        duration=datetime.now() - start_time,
    )
