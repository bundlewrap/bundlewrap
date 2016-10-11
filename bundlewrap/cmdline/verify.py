# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from sys import exit

from ..concurrency import WorkerPool
from ..utils.cmdline import get_target_nodes
from ..utils.text import error_summary, mark_for_translation as _
from ..utils.ui import io


def stats_summary(node_stats):
    for node in node_stats.keys():
        node_stats[node]['total'] = node_stats[node]['good'] + node_stats[node]['bad']
        try:
            node_stats[node]['health'] = \
                (node_stats[node]['good'] / float(node_stats[node]['total'])) * 100.0
        except ZeroDivisionError:
            node_stats[node]['health'] = 0

    total_items = 0
    total_good = 0

    node_ranking = []

    for node_name, stats in node_stats.items():
        total_items += stats['total']
        total_good += stats['good']
        node_ranking.append((
            stats['health'],
            node_name,
            stats['good'],
            stats['total'],
        ))

    node_ranking = sorted(node_ranking)
    node_ranking.reverse()

    try:
        overall_health = (total_good / float(total_items)) * 100.0
    except ZeroDivisionError:
        overall_health = 0

    if len(node_ranking) == 1:
        io.stdout(_("node health:  {health:.1f}%  ({good}/{total} OK)").format(
            good=node_ranking[0][2],
            health=node_ranking[0][0],
            total=node_ranking[0][3],
        ))
    else:
        io.stdout(_("node health:"))
        for health, node_name, good, total in node_ranking:
            io.stdout(_("  {health}%  {node_name}  ({good}/{total} OK)").format(
                good=good,
                health="{:.1f}".format(health).rjust(5, " "),
                node_name=node_name,
                total=total,
            ))
        io.stdout(_("overall:  {health:.1f}%  ({good}/{total} OK)").format(
            good=total_good,
            health=overall_health,
            total=total_items,
        ))


def bw_verify(repo, args):
    errors = []
    node_stats = {}
    pending_nodes = get_target_nodes(repo, args['target'], adhoc_nodes=args['adhoc_nodes'])

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

    if args['summary']:
        for line in stats_summary(node_stats):
            io.stdout(line)

    error_summary(errors)

    exit(1 if errors else 0)
