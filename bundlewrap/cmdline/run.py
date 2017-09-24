# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from datetime import datetime
try:
    from itertools import zip_longest
except ImportError:  # Python 2
    from itertools import izip_longest as zip_longest
from sys import exit

from ..concurrency import WorkerPool
from ..utils import SkipList
from ..utils.cmdline import get_target_nodes
from ..utils.table import ROW_SEPARATOR, render_table
from ..utils.text import mark_for_translation as _
from ..utils.text import blue, bold, error_summary, green, red, yellow
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

    result = node.run(
        command,
        may_fail=True,
        log_output=True,
    )

    node.repo.hooks.node_run_end(
        node.repo,
        node,
        command,
        duration=result.duration,
        return_code=result.return_code,
        stdout=result.stdout,
        stderr=result.stderr,
    )
    return result


def stats_summary(results, include_stdout, include_stderr):
    rows = [[
        bold(_("node")),
        bold(_("return code")),
        bold(_("time")),
    ], ROW_SEPARATOR]
    if include_stdout:
        rows[0].append(bold(_("stdout")))
    if include_stderr:
        rows[0].append(bold(_("stderr")))

    for node_name, result in sorted(results.items()):
        row = [node_name]
        if result.return_code == 0:
            row.append(green(str(result.return_code)))
        else:
            row.append(red(str(result.return_code)))
        row.append(format_duration(result.duration, msec=True))
        rows.append(row)
        if include_stdout or include_stderr:
            stdout = result.stdout.decode('utf-8', errors='replace').strip().split("\n")
            stderr = result.stderr.decode('utf-8', errors='replace').strip().split("\n")
            if include_stdout:
                row.append(stdout[0])
            if include_stderr:
                row.append(stderr[0])
            for stdout_line, stderr_line in list(zip_longest(stdout, stderr, fillvalue=""))[1:]:
                continuation_row = ["", "", ""]
                if include_stdout:
                    continuation_row.append(stdout_line)
                if include_stderr:
                    continuation_row.append(stderr_line)
                rows.append(continuation_row)
            rows.append(ROW_SEPARATOR)

    if include_stdout or include_stderr:
        # remove last ROW_SEPARATOR
        rows = rows[:-1]
    for line in render_table(rows, alignments={1: 'right', 2: 'right'}):
        io.stdout("{x} {line}".format(x=blue("i"), line=line))


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
    results = {}
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
        results[task_id] = return_value
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

    if args['summary']:
        stats_summary(results, args['stdout_table'], args['stderr_table'])
    error_summary(errors)

    repo.hooks.run_end(
        repo,
        args['target'],
        target_nodes,
        args['command'],
        duration=datetime.now() - start_time,
    )

    exit(1 if errors else 0)
