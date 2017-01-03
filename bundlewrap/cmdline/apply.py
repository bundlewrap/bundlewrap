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
    yellow,
    yellow_unless_zero,
)
from ..utils.time import format_duration
from ..utils.ui import io


def bw_apply(repo, args):
    errors = []
    target_nodes = get_target_nodes(repo, args['target'], adhoc_nodes=args['adhoc_nodes'])
    pending_nodes = target_nodes[:]

    repo.hooks.apply_start(
        repo,
        args['target'],
        target_nodes,
        interactive=args['interactive'],
    )

    start_time = datetime.now()
    results = []

    def tasks_available():
        return bool(pending_nodes)

    def next_task():
        node = pending_nodes.pop()
        return {
            'target': node.apply,
            'task_id': node.name,
            'kwargs': {
                'autoskip_selector': args['autoskip'],
                'force': args['force'],
                'interactive': args['interactive'],
                'workers': args['item_workers'],
                'profiling': args['profiling'],
            },
        }

    def handle_result(task_id, return_value, duration):
        if return_value is None:  # node skipped because it had no items
            return
        results.append(return_value)
        if args['profiling']:
            total_time = 0.0
            io.stdout(_("  {}").format(bold(task_id)))
            io.stdout(_("  {} BEGIN PROFILING DATA "
                        "(most expensive items first)").format(bold(task_id)))
            io.stdout(_("  {}    seconds   item").format(bold(task_id)))
            for time_elapsed, item_id in return_value.profiling_info:
                io.stdout("  {} {:10.3f}   {}".format(
                    bold(task_id),
                    time_elapsed.total_seconds(),
                    item_id,
                ))
                total_time += time_elapsed.total_seconds()
            io.stdout(_("  {} {:10.3f}   (total)").format(bold(task_id), total_time))
            io.stdout(_("  {} END PROFILING DATA").format(bold(task_id)))
            io.stdout(_("  {}").format(bold(task_id)))

    def handle_exception(task_id, exception, traceback):
        msg = "{}: {}".format(task_id, exception)
        io.stderr(traceback)
        io.stderr(repr(exception))
        io.stderr(msg)
        errors.append(msg)

    worker_pool = WorkerPool(
        tasks_available,
        next_task,
        handle_result=handle_result,
        handle_exception=handle_exception,
        pool_id="apply",
        workers=args['node_workers'],
    )
    worker_pool.run()

    total_duration = datetime.now() - start_time

    if args['summary'] and results:
        stats_summary(results, total_duration)
    error_summary(errors)

    repo.hooks.apply_end(
        repo,
        args['target'],
        target_nodes,
        duration=total_duration,
    )

    exit(1 if errors else 0)


def stats_summary(results, total_duration):
    totals = {
        'items': 0,
        'correct': 0,
        'fixed': 0,
        'skipped': 0,
        'failed': 0,
    }
    headings = {
        'node_name': _("node"),
        'items': _("items"),
        'correct': _("OK"),
        'fixed': _("fixed"),
        'skipped': _("skipped"),
        'failed': _("failed"),
        'duration': _("time"),
        'totals_row': _("total ({} nodes)").format(len(results)),
    }

    max_duration_length = max(len(headings['duration']), len(format_duration(total_duration)))
    max_node_name_length = max(len(headings['node_name']), len(headings['totals_row']))

    for result in results:
        totals['items'] += len(result.profiling_info)
        max_duration_length = max(len(format_duration(result.duration)), max_duration_length)
        max_node_name_length = max(len(result.node_name), max_node_name_length)
        for metric in ('correct', 'fixed', 'skipped', 'failed'):
            totals[metric] += getattr(result, metric)

    column_width = {
        'duration': max_duration_length,
        'node_name': max_node_name_length,
    }
    for column, total in totals.items():
        column_width[column] = max(len(str(total)), len(headings[column]))

    io.stdout("{x} ╭─{node}─┬─{items}─┬─{correct}─┬─{fixed}─┬─{skipped}─┬─{failed}─┬─{duration}─╮".format(
        node="─" * column_width['node_name'],
        items="─" * column_width['items'],
        correct="─" * column_width['correct'],
        fixed="─" * column_width['fixed'],
        skipped="─" * column_width['skipped'],
        failed="─" * column_width['failed'],
        duration="─" * column_width['duration'],
        x=blue("i"),
    ))
    io.stdout("{x} │ {node} │ {items} │ {correct} │ {fixed} │ {skipped} │ {failed} │ {duration} │".format(
        node=bold(headings['node_name'].ljust(column_width['node_name'])),
        items=headings['items'].ljust(column_width['items']),
        correct=headings['correct'].ljust(column_width['correct']),
        fixed=green(headings['fixed'].ljust(column_width['fixed'])),
        skipped=yellow(headings['skipped'].ljust(column_width['skipped'])),
        failed=red(headings['failed'].ljust(column_width['failed'])),
        duration=headings['duration'].ljust(column_width['duration']),
        x=blue("i"),
    ))
    io.stdout("{x} ├─{node}─┼─{items}─┼─{correct}─┼─{fixed}─┼─{skipped}─┼─{failed}─┼─{duration}─┤".format(
        node="─" * column_width['node_name'],
        items="─" * column_width['items'],
        correct="─" * column_width['correct'],
        fixed="─" * column_width['fixed'],
        skipped="─" * column_width['skipped'],
        failed="─" * column_width['failed'],
        duration="─" * column_width['duration'],
        x=blue("i"),
    ))
    for result in results:
        io.stdout("{x} │ {node} │ {items} │ {correct} │ {fixed} │ {skipped} │ {failed} │ {duration} │".format(
            node=result.node_name.ljust(column_width['node_name']),
            items=str(len(result.profiling_info)).rjust(column_width['items']),
            correct=str(result.correct).rjust(column_width['correct']),
            fixed=green_unless_zero(result.fixed, column_width['fixed']),
            skipped=yellow_unless_zero(result.skipped, column_width['skipped']),
            failed=red_unless_zero(result.failed, column_width['failed']),
            duration=format_duration(result.duration).rjust(column_width['duration']),
            x=blue("i"),
        ))
    if len(results) > 1:
        io.stdout("{x} ├─{node}─┼─{items}─┼─{correct}─┼─{fixed}─┼─{skipped}─┼─{failed}─┼─{duration}─┤".format(
            node="─" * column_width['node_name'],
            items="─" * column_width['items'],
            correct="─" * column_width['correct'],
            fixed="─" * column_width['fixed'],
            skipped="─" * column_width['skipped'],
            failed="─" * column_width['failed'],
            duration="─" * column_width['duration'],
            x=blue("i"),
        ))
        io.stdout("{x} │ {node} │ {items} │ {correct} │ {fixed} │ {skipped} │ {failed} │ {duration} │".format(
            node=bold(headings['totals_row'].ljust(column_width['node_name'])),
            items=str(totals['items']).rjust(column_width['items']),
            correct=str(totals['correct']).rjust(column_width['correct']),
            fixed=green_unless_zero(totals['fixed'], column_width['fixed']),
            skipped=yellow_unless_zero(totals['skipped'], column_width['skipped']),
            failed=red_unless_zero(totals['failed'], column_width['failed']),
            duration=format_duration(total_duration).rjust(column_width['duration']),
            x=blue("i"),
        ))
    io.stdout("{x} ╰─{node}─┴─{items}─┴─{correct}─┴─{fixed}─┴─{skipped}─┴─{failed}─┴─{duration}─╯".format(
        node="─" * column_width['node_name'],
        items="─" * column_width['items'],
        correct="─" * column_width['correct'],
        fixed="─" * column_width['fixed'],
        skipped="─" * column_width['skipped'],
        failed="─" * column_width['failed'],
        duration="─" * column_width['duration'],
        x=blue("i"),
    ))
