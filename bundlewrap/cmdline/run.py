# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from datetime import datetime

from ..concurrency import WorkerPool
from ..exceptions import NodeLockedException
from ..utils.cmdline import get_target_nodes
from ..utils.text import mark_for_translation as _
from ..utils.text import bold, error_summary, green, red, yellow
from ..utils.ui import io


def run_on_node(node, command, may_fail, ignore_locks, log_output):
    if node.dummy:
        io.stdout(_("{x}  {node} is a dummy node").format(node=bold(node.name), x=yellow("!")))
        return

    node.repo.hooks.node_run_start(
        node.repo,
        node,
        command,
    )

    start = datetime.now()
    result = node.run(
        command,
        may_fail=may_fail,
        log_output=log_output,
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
        io.stdout("{x} {node}  {msg}".format(
            msg=_("completed successfully after {time}s").format(
                time=duration.total_seconds(),
            ),
            node=bold(node.name),
            x=green("✓"),
        ))
    else:
        io.stderr("{x} {node}  {msg}".format(
            msg=_("failed after {time}s (return code {rcode})").format(
                rcode=result.return_code,
                time=duration.total_seconds(),
            ),
            node=bold(node.name),
            x=red("✘"),
        ))


def bw_run(repo, args):
    errors = []
    target_nodes = get_target_nodes(repo, args['target'], adhoc_nodes=args['adhoc_nodes'])
    pending_nodes = target_nodes[:]

    repo.hooks.run_start(
        repo,
        args['target'],
        target_nodes,
        args['command'],
    )
    start_time = datetime.now()

    def tasks_available():
        return bool(pending_nodes)

    def next_task():
        node = pending_nodes.pop()
        return {
            'target': run_on_node,
            'task_id': node.name,
            'args': (
                node,
                args['command'],
                args['may_fail'],
                args['ignore_locks'],
                True,
            ),
        }

    def handle_exception(task_id, exception, traceback):
        if isinstance(exception, NodeLockedException):
            msg = _(
                "{node_bold}  locked by {user} "
                "(see `bw lock show {node}` for details)"
            ).format(
                node_bold=bold(task_id),
                node=task_id,
                user=exception.args[0]['user'],
            )
        else:
            msg = "{}  {}".format(bold(task_id), exception)
            io.stderr(traceback)
            io.stderr(repr(exception))
        io.stderr("{} {}".format(red("!"), msg))
        errors.append(msg)

    worker_pool = WorkerPool(
        tasks_available,
        next_task,
        handle_exception=handle_exception,
        pool_id="run",
        workers=args['node_workers'],
    )
    worker_pool.run()

    error_summary(errors)

    repo.hooks.run_end(
        repo,
        args['target'],
        target_nodes,
        args['command'],
        duration=datetime.now() - start_time,
    )
