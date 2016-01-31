# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from datetime import datetime

from ..concurrency import WorkerPool
from ..exceptions import WorkerException
from ..utils.cmdline import get_target_nodes
from ..utils.text import mark_for_translation as _
from ..utils.text import bold, error_summary, green, red


def run_on_node(node, command, may_fail, log_output):
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
        yield "{x} [{node}] {msg}".format(
            msg=_("completed successfully after {time}s").format(
                time=duration.total_seconds(),
            ),
            node=bold(node.name),
            x=green("✓"),
        )
    else:
        yield "{x} [{node}] {msg}".format(
            msg=_("failed after {time}s (return code {rcode})").format(
                rcode=result.return_code,
                time=duration.total_seconds(),
            ),
            node=bold(node.name),
            x=red("✘"),
        )


def bw_run(repo, args):
    errors = []
    target_nodes = get_target_nodes(repo, args['target'])
    pending_nodes = target_nodes[:]

    repo.hooks.run_start(
        repo,
        args['target'],
        target_nodes,
        args['command'],
    )
    start_time = datetime.now()

    with WorkerPool(workers=args['node_workers']) as worker_pool:
        while worker_pool.keep_running():
            try:
                msg = worker_pool.get_event()
            except WorkerException as e:
                msg = "{x} [{node}] {msg}".format(
                    msg=e.wrapped_exception,
                    node=bold(e.task_id),
                    x=red("!"),
                )
                if args['debug']:
                    yield e.traceback
                yield msg
                errors.append(msg)
                continue
            if msg['msg'] == 'REQUEST_WORK':
                if pending_nodes:
                    node = pending_nodes.pop()
                    worker_pool.start_task(
                        msg['wid'],
                        run_on_node,
                        task_id=node.name,
                        args=(
                            node,
                            args['command'],
                            args['may_fail'],
                            True,
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
        args['target'],
        target_nodes,
        args['command'],
        duration=datetime.now() - start_time,
    )
