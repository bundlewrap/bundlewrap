from datetime import datetime
from sys import exit

from ..concurrency import WorkerPool
from ..exceptions import GracefulException
from ..utils.cmdline import count_items, get_target_nodes, verify_autoskip_selectors
from ..utils.table import ROW_SEPARATOR, render_table
from ..utils.text import (
    blue,
    bold,
    cyan,
    cyan_unless_zero,
    error_summary,
    format_duration,
    green,
    green_unless_zero,
    mark_for_translation as _,
    red,
    red_unless_zero,
)
from ..utils.ui import io


def stats_summary(results, totals, total_duration):
    rows = [[
        bold(_("node")),
        _("items"),
        green(_("good")),
        red(_("bad")),
        cyan(_("unknown")),
        _("health"),
        _("duration"),
    ], ROW_SEPARATOR]

    for result in sorted(results):
        rows.append([
            result.node_name,
            str(result.total),
            green_unless_zero(result.correct),
            red_unless_zero(result.bad),
            cyan_unless_zero(result.unknown),
            "{0:.1f}%".format(result.health),
            format_duration(result.duration),
        ])


    if len(results) > 1:
        rows.append(ROW_SEPARATOR)
        rows.append([
            bold(_("total ({} nodes)").format(len(results))),
            str(totals['items']),
            green_unless_zero(totals['correct']),
            red_unless_zero(totals['bad']),
            cyan_unless_zero(totals['unknown']),
            "{0:.1f}%".format(totals['health']),
            format_duration(total_duration),
        ])

    alignments = {
        1: 'right',
        2: 'right',
        3: 'right',
        4: 'right',
        5: 'right',
        6: 'right',
        7: 'right',
    }

    for line in render_table(rows, alignments=alignments):
        io.stdout("{x} {line}".format(x=blue("i"), line=line))


def bw_verify(repo, args):
    errors = []
    target_nodes = get_target_nodes(repo, args['targets'])
    pending_nodes = target_nodes.copy()

    try:
        repo.hooks.verify_start(
            repo=repo,
            target=args['targets'],
            nodes=target_nodes,
        )
    except GracefulException as exc:
        io.stderr(_("{x} verify aborted by hook ({reason})").format(
            reason=str(exc) or _("no reason given"),
            x=red("!!!"),
        ))
        exit(1)

    io.progress_set_total(count_items(pending_nodes))

    selectors_not_matching = verify_autoskip_selectors(pending_nodes, args['autoskip'])
    if selectors_not_matching:
        io.stderr(_("{x} the following selectors for --skip do not match any items: {selectors}").format(
            x=red("!!!"),
            selectors=' '.join(sorted(selectors_not_matching)),
        ))
        exit(1)

    start_time = datetime.now()
    results = []

    def tasks_available():
        return bool(pending_nodes)

    def next_task():
        node = pending_nodes.pop()
        return {
            'target': node.verify,
            'task_id': node.name,
            'kwargs': {
                'autoonly_selector': args['autoonly'],
                'autoskip_selector': args['autoskip'],
                'show_all': args['show_all'],
                'show_diff': args['show_diff'],
                'workers': args['item_workers'],
            },
        }

    def handle_result(task_id, return_value, duration):
        if return_value is None: # node skipped
            return
        results.append(return_value)

    def handle_exception(task_id, exception, traceback):
        msg = "{}: {}".format(
            task_id,
            exception,
        )
        io.stderr(traceback)
        io.stderr(repr(exception))
        io.stderr(msg)
        errors.append(msg)

    worker_pool = WorkerPool(
        tasks_available,
        next_task,
        handle_result=handle_result,
        handle_exception=handle_exception,
        pool_id="verify",
        workers=args['node_workers'],
    )
    worker_pool.run()

    total_duration = datetime.now() - start_time
    totals = stats(results)

    if args['summary'] and results:
        stats_summary(results, totals, total_duration)

    error_summary(errors)

    repo.hooks.verify_end(
        repo=repo,
        target=args['targets'],
        nodes=target_nodes,
        duration=total_duration,
    )

    exit(1 if errors else 0)


def stats(results):
    totals = {
        'items': 0,
        'correct': 0,
        'bad': 0,
        'unknown': 0,
        'health': 0,
    }
    for result in results:
        totals['items'] += result.total
        for metric in ('correct', 'bad', 'unknown', 'health'):
            totals[metric] += getattr(result, metric)

    try:
        totals['health'] = totals['health'] / len(results)
    except ZeroDivisionError:
        totals['health'] = 0

    return totals
