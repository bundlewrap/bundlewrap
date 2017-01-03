# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from datetime import datetime
from sys import exit

from ..concurrency import WorkerPool
from ..utils.cmdline import get_target_nodes
from ..utils.text import (
    blue,
    bold,
    error_summary,
    green,
    green_unless_zero,
    mark_for_translation as _,
    red,
    red_unless_zero,
)
from ..utils.time import format_duration
from ..utils.ui import io


def stats_summary(node_stats, total_duration):
    for node in node_stats.keys():
        node_stats[node]['total'] = node_stats[node]['good'] + node_stats[node]['bad']
        try:
            node_stats[node]['health'] = \
                (node_stats[node]['good'] / float(node_stats[node]['total'])) * 100.0
        except ZeroDivisionError:
            node_stats[node]['health'] = 0

    totals = {
        'items': 0,
        'good': 0,
        'bad': 0,
    }
    node_ranking = []

    for node_name, stats in node_stats.items():
        totals['items'] += stats['total']
        totals['good'] += stats['good']
        totals['bad'] += stats['bad']
        node_ranking.append((
            stats['health'],
            node_name,
            stats['total'],
            stats['good'],
            stats['bad'],
            stats['duration'],
        ))

    node_ranking = sorted(node_ranking, reverse=True)

    try:
        totals['health'] = (totals['good'] / float(totals['items'])) * 100.0
    except ZeroDivisionError:
        totals['health'] = 0

    headings = {
        'node_name': _("node"),
        'items': _("items"),
        'good': _("good"),
        'bad': _("bad"),
        'health': _("health"),
        'duration': _("time"),
        'totals_row': _("total ({} nodes)").format(len(node_stats.keys())),
    }

    max_duration_length = max(len(headings['duration']), len(format_duration(total_duration)))
    max_node_name_length = max(len(headings['node_name']), len(headings['totals_row']))

    for node_name, stats in node_stats.items():
        max_duration_length = max(len(format_duration(stats['duration'])), max_duration_length)
        max_node_name_length = max(len(node_name), max_node_name_length)

    column_width = {
        'duration': max_duration_length,
        'node_name': max_node_name_length,
    }
    for column, total in totals.items():
        column_width[column] = max(len(str(total)), len(headings[column]))
    column_width['health'] = 6

    io.stdout("{x} ╭─{node}─┬─{items}─┬─{good}─┬─{bad}─┬─{health}─┬─{duration}─╮".format(
        node="─" * column_width['node_name'],
        items="─" * column_width['items'],
        good="─" * column_width['good'],
        bad="─" * column_width['bad'],
        health="─" * column_width['health'],
        duration="─" * column_width['duration'],
        x=blue("i"),
    ))
    io.stdout("{x} │ {node} │ {items} │ {good} │ {bad} │ {health} │ {duration} │".format(
        node=bold(headings['node_name'].ljust(column_width['node_name'])),
        items=headings['items'].ljust(column_width['items']),
        good=green(headings['good'].ljust(column_width['good'])),
        bad=red(headings['bad'].ljust(column_width['bad'])),
        health=headings['health'].ljust(column_width['health']),
        duration=headings['duration'].ljust(column_width['duration']),
        x=blue("i"),
    ))
    io.stdout("{x} ├─{node}─┼─{items}─┼─{good}─┼─{bad}─┼─{health}─┼─{duration}─┤".format(
        node="─" * column_width['node_name'],
        items="─" * column_width['items'],
        good="─" * column_width['good'],
        bad="─" * column_width['bad'],
        health="─" * column_width['health'],
        duration="─" * column_width['duration'],
        x=blue("i"),
    ))
    for health, node_name, items, good, bad, duration in node_ranking:
        io.stdout("{x} │ {node} │ {items} │ {good} │ {bad} │ {health} │ {duration} │".format(
            node=node_name.ljust(column_width['node_name']),
            items=str(items).rjust(column_width['items']),
            good=green_unless_zero(good, column_width['good']),
            bad=red_unless_zero(bad, column_width['bad']),
            health="{0:.1f}%".format(health).rjust(column_width['health']),
            duration=format_duration(duration).rjust(column_width['duration']),
            x=blue("i"),
        ))
    if len(node_ranking) > 1:
        io.stdout("{x} ├─{node}─┼─{items}─┼─{good}─┼─{bad}─┼─{health}─┼─{duration}─┤".format(
            node="─" * column_width['node_name'],
            items="─" * column_width['items'],
            good="─" * column_width['good'],
            bad="─" * column_width['bad'],
            health="─" * column_width['health'],
            duration="─" * column_width['duration'],
            x=blue("i"),
        ))
        io.stdout("{x} │ {node} │ {items} │ {good} │ {bad} │ {health} │ {duration} │".format(
            node=bold(headings['totals_row'].ljust(column_width['node_name'])),
            items=str(totals['items']).rjust(column_width['items']),
            good=green_unless_zero(totals['good'], column_width['good']),
            bad=red_unless_zero(totals['bad'], column_width['bad']),
            health="{0:.1f}%".format(totals['health']).rjust(column_width['health']),
            duration=format_duration(total_duration).rjust(column_width['duration']),
            x=blue("i"),
        ))
    io.stdout("{x} ╰─{node}─┴─{items}─┴─{good}─┴─{bad}─┴─{health}─┴─{duration}─╯".format(
        node="─" * column_width['node_name'],
        items="─" * column_width['items'],
        good="─" * column_width['good'],
        bad="─" * column_width['bad'],
        health="─" * column_width['health'],
        duration="─" * column_width['duration'],
        x=blue("i"),
    ))


def bw_verify(repo, args):
    errors = []
    node_stats = {}
    pending_nodes = get_target_nodes(repo, args['target'], adhoc_nodes=args['adhoc_nodes'])
    start_time = datetime.now()

    def tasks_available():
        return bool(pending_nodes)

    def next_task():
        node = pending_nodes.pop()
        return {
            'target': node.verify,
            'task_id': node.name,
            'kwargs': {
                'show_all': args['show_all'],
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
