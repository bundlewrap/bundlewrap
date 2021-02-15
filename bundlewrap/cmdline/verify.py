from datetime import datetime
from sys import exit

from ..concurrency import WorkerPool
from ..utils.cmdline import count_items, get_target_nodes
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


def stats_summary(node_stats, total_duration):
    for node in node_stats.keys():
        node_stats[node]['total'] = sum([
            node_stats[node]['good'],
            node_stats[node]['bad'],
            node_stats[node]['unknown'],
        ])
        try:
            node_stats[node]['health'] = \
                (node_stats[node]['good'] / float(node_stats[node]['total'])) * 100.0
        except ZeroDivisionError:
            node_stats[node]['health'] = 0

    totals = {
        'items': 0,
        'good': 0,
        'bad': 0,
        'unknown': 0,
    }
    node_ranking = []

    for node_name, stats in node_stats.items():
        totals['items'] += stats['total']
        totals['good'] += stats['good']
        totals['bad'] += stats['bad']
        totals['unknown'] += stats['unknown']
        node_ranking.append((
            stats['health'],
            node_name,
            stats['total'],
            stats['good'],
            stats['bad'],
            stats['unknown'],
            stats['duration'],
        ))

    node_ranking = sorted(node_ranking, reverse=True)

    try:
        totals['health'] = (totals['good'] / float(totals['items'])) * 100.0
    except ZeroDivisionError:
        totals['health'] = 0

    rows = [[
        bold(_("node")),
        _("items"),
        green(_("good")),
        red(_("bad")),
        cyan(_("unknown")),
        _("health"),
        _("duration"),
    ], ROW_SEPARATOR]

    for health, node_name, items, good, bad, unknown, duration in node_ranking:
        rows.append([
            node_name,
            str(items),
            green_unless_zero(good),
            red_unless_zero(bad),
            cyan_unless_zero(unknown),
            "{0:.1f}%".format(health),
            format_duration(duration),
        ])

    if len(node_ranking) > 1:
        rows.append(ROW_SEPARATOR)
        rows.append([
            bold(_("total ({} nodes)").format(len(node_stats.keys()))),
            str(totals['items']),
            green_unless_zero(totals['good']),
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
    node_stats = {}
    pending_nodes = get_target_nodes(repo, args['targets'])
    start_time = datetime.now()
    io.progress_set_total(count_items(pending_nodes))

    def tasks_available():
        return bool(pending_nodes)

    def next_task():
        node = pending_nodes.pop()
        return {
            'target': node.verify,
            'task_id': node.name,
            'kwargs': {
                'show_all': args['show_all'],
                'show_diff': args['show_diff'],
                'workers': args['item_workers'],
            },
        }

    def handle_result(task_id, return_value, duration):
        node_stats[task_id] = return_value

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

    if args['summary'] and node_stats:
        stats_summary(node_stats, datetime.now() - start_time)

    error_summary(errors)

    exit(1 if errors else 0)
