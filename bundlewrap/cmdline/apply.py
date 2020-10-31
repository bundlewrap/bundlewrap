from datetime import datetime
from sys import exit

from ..concurrency import WorkerPool
from ..exceptions import GracefulApplyException, ItemDependencyLoop
from ..utils import SkipList
from ..utils.cmdline import count_items, get_target_nodes
from ..utils.plot import explain_item_dependency_loop
from ..utils.table import ROW_SEPARATOR, render_table
from ..utils.text import (
    blue,
    bold,
    error_summary,
    format_duration,
    green,
    green_unless_zero,
    mark_for_translation as _,
    red,
    red_unless_zero,
    yellow,
    yellow_unless_zero,
)
from ..utils.ui import io


def bw_apply(repo, args):
    errors = []
    target_nodes = get_target_nodes(repo, args['targets'])
    pending_nodes = target_nodes.copy()

    try:
        repo.hooks.apply_start(
            repo,
            args['targets'],
            target_nodes,
            interactive=args['interactive'],
        )
    except GracefulApplyException as exc:
        io.stderr(_("{x} apply aborted by hook ({reason})").format(
            reason=str(exc) or _("no reason given"),
            x=red("!!!"),
        ))
        exit(1)

    io.progress_set_total(count_items(pending_nodes))

    start_time = datetime.now()
    results = []
    skip_list = SkipList(args['resume_file'])

    def tasks_available():
        return bool(pending_nodes)

    def next_task():
        node = pending_nodes.pop()
        return {
            'target': node.apply,
            'task_id': node.name,
            'kwargs': {
                'autoskip_selector': args['autoskip'],
                'autoonly_selector': args['autoonly'],
                'force': args['force'],
                'interactive': args['interactive'],
                'skip_list': skip_list,
                'workers': args['item_workers'],
            },
        }

    def handle_result(task_id, return_value, duration):
        if return_value is None:  # node skipped
            return
        skip_list.add(task_id)
        results.append(return_value)

    def handle_exception(task_id, exception, traceback):
        msg = _("{x} {node}  {msg}").format(
            node=bold(task_id),
            msg=exception,
            x=red("!"),
        )
        if isinstance(exception, ItemDependencyLoop):
            for line in explain_item_dependency_loop(exception, task_id):
                io.stderr(line)
                errors.append(line)
        elif isinstance(exception, GracefulApplyException):
            errors.append(msg)
        else:
            io.stderr(traceback)
            io.stderr(repr(exception))
            io.stderr(msg)
            errors.append(msg)

    worker_pool = WorkerPool(
        tasks_available,
        next_task,
        handle_result=handle_result,
        handle_exception=handle_exception,
        cleanup=skip_list.dump,
        pool_id="apply",
        workers=args['node_workers'],
    )
    worker_pool.run()

    total_duration = datetime.now() - start_time
    totals = stats(results)

    if args['summary'] and results:
        stats_summary(results, totals, total_duration)
    error_summary(errors)

    repo.hooks.apply_end(
        repo,
        args['targets'],
        target_nodes,
        duration=total_duration,
    )

    exit(1 if errors or totals['failed'] else 0)


def stats(results):
    totals = {
        'items': 0,
        'correct': 0,
        'fixed': 0,
        'skipped': 0,
        'failed': 0,
    }
    for result in results:
        totals['items'] += result.total
        for metric in ('correct', 'fixed', 'skipped', 'failed'):
            totals[metric] += getattr(result, metric)
    return totals


def stats_summary(results, totals, total_duration):
    rows = [[
        bold(_("node")),
        _("items"),
        _("OK"),
        green(_("fixed")),
        yellow(_("skipped")),
        red(_("failed")),
        _("time"),
    ], ROW_SEPARATOR]

    for result in sorted(results):
        rows.append([
            result.node_name,
            str(result.total),
            str(result.correct),
            green_unless_zero(result.fixed),
            yellow_unless_zero(result.skipped),
            red_unless_zero(result.failed),
            format_duration(result.duration),
        ])

    if len(results) > 1:
        rows.append(ROW_SEPARATOR)
        rows.append([
            bold(_("total ({} nodes)").format(len(results))),
            str(totals['items']),
            str(totals['correct']),
            green_unless_zero(totals['fixed']),
            yellow_unless_zero(totals['skipped']),
            red_unless_zero(totals['failed']),
            format_duration(total_duration),
        ])

    alignments = {
        1: 'right',
        2: 'right',
        3: 'right',
        4: 'right',
        5: 'right',
        6: 'right',
    }

    for line in render_table(rows, alignments=alignments):
        io.stdout("{x} {line}".format(x=blue("i"), line=line))
