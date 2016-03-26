# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from ..concurrency import WorkerPool
from ..exceptions import WorkerException
from ..utils.cmdline import get_target_nodes
from ..utils.text import error_summary, mark_for_translation as _


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
        yield _("node health:  {health:.1f}%  ({good}/{total} OK)").format(
            good=node_ranking[0][2],
            health=node_ranking[0][0],
            total=node_ranking[0][3],
        )
    else:
        yield _("node health:")
        for health, node_name, good, total in node_ranking:
            yield _("  {health}%  {node_name}  ({good}/{total} OK)").format(
                good=good,
                health="{:.1f}".format(health).rjust(5, " "),
                node_name=node_name,
                total=total,
            )
        yield _("overall:  {health:.1f}%  ({good}/{total} OK)").format(
            good=total_good,
            health=overall_health,
            total=total_items,
        )


def bw_verify(repo, args):
    errors = []
    node_stats = {}
    pending_nodes = get_target_nodes(repo, args['target'])
    with WorkerPool(workers=args['node_workers']) as worker_pool:
        while pending_nodes or worker_pool.workers_are_running:
            while pending_nodes and worker_pool.workers_are_available:
                node = pending_nodes.pop()
                worker_pool.start_task(
                    node.verify,
                    task_id=node.name,
                    kwargs={
                        'show_all': args['show_all'],
                        'workers': args['item_workers'],
                    },
                )
            try:
                result = worker_pool.get_result()
            except WorkerException as exc:
                msg = "{}: {}".format(
                    exc.kwargs['task_id'],
                    exc.wrapped_exception,
                )
                if args['debug']:
                    yield exc.wrapped_exception.traceback
                yield msg
                errors.append(msg)
            else:
                node_stats[result['task_id']] = result['return_value']

    if args['summary']:
        for line in stats_summary(node_stats):
            yield line

    error_summary(errors)

    yield 1 if errors else 0
