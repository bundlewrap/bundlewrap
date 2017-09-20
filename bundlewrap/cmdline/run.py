# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from datetime import datetime

from ..concurrency import WorkerPool
from ..utils import SkipList
from ..utils.cmdline import get_target_nodes
from ..utils.text import mark_for_translation as _
from ..utils.text import bold, error_summary, green, red, yellow
from ..utils.time import format_duration
from ..utils.ui import io


def run_on_node(node, command, skip_list):
    if node.dummy:
        io.stdout(_("{x} {node}  is a dummy node").format(node=bold(node.name), x=yellow("»")))
        return None

    if node.name in skip_list:
        io.stdout(_("{x} {node}  skipped by --resume-file").format(node=bold(node.name), x=yellow("»")))
        return None

    node.repo.hooks.node_run_start(
        node.repo,
        node,
        command,
    )

    start = datetime.now()
    result = node.run(
        command,
        may_fail=True,
        log_output=True,
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
            msg=_("completed successfully after {time}").format(
                time=format_duration(duration, msec=True),
            ),
            node=bold(node.name),
            x=green("✓"),
        ))
    else:
        io.stderr("{x} {node}  {msg}".format(
            msg=_("failed after {time}s (return code {rcode})").format(
                rcode=result.return_code,
                time=format_duration(duration, msec=True),
            ),
            node=bold(node.name),
            x=red("✘"),
        ))
    return result.return_code


def bw_run(repo, args):
    errors = []
    target_nodes = get_target_nodes(repo, args['target'], adhoc_nodes=args['adhoc_nodes'])
    pending_nodes = target_nodes[:]
    io.progress_set_total(len(pending_nodes))

    repo.hooks.run_start(
        repo,
        args['target'],
        target_nodes,
        args['command'],
    )
    start_time = datetime.now()

    skip_list = SkipList(args['resume_file'])

    def tasks_available():
        return bool(pending_nodes)

    def next_task():
        node = pending_nodes.pop()
        return {
            'target': run_on_node,
            'task_id': node.name,
            'args': (
                node,
                " ".join(args['command']),
                skip_list,
            ),
        }

    def handle_result(task_id, return_value, duration):
        io.progress_advance()
        if return_value == 0:
            skip_list.add(task_id)

    def handle_exception(task_id, exception, traceback):
        io.progress_advance()
        msg = "{}  {}".format(bold(task_id), exception)
        io.stderr(traceback)
        io.stderr(repr(exception))
        io.stderr("{} {}".format(red("!"), msg))
        errors.append(msg)

    worker_pool = WorkerPool(
        tasks_available,
        next_task,
        handle_result=handle_result,
        handle_exception=handle_exception,
        cleanup=skip_list.dump,
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
