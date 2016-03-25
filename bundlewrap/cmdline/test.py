# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from copy import copy

from ..concurrency import WorkerPool
from ..plugins import PluginManager
from ..utils.cmdline import get_target_nodes
from ..utils.text import bold, green, mark_for_translation as _, red
from ..utils.ui import io


def bw_test(repo, args):
    if args['target']:
        pending_nodes = get_target_nodes(repo, args['target'])
    else:
        pending_nodes = copy(list(repo.nodes))
    with WorkerPool(workers=args['node_workers']) as worker_pool:
        while pending_nodes or worker_pool.workers_are_running:
            while pending_nodes and worker_pool.workers_are_available:
                node = pending_nodes.pop()
                worker_pool.start_task(
                    node.test,
                    task_id=node.name,
                    kwargs={
                        'workers': args['item_workers'],
                    },
                )

            worker_pool.get_result()

    checked_groups = []
    for group in repo.groups:
        if group in checked_groups:
            continue
        with io.job(_("  {group}  checking for subgroup loops...").format(group=group.name)):
            checked_groups.extend(group.subgroups)  # the subgroups property has the check built in
        yield _("{x} {group}  has no subgroup loops").format(
            x=green("✓"),
            group=bold(group.name),
        )

    # check for plugin inconsistencies
    if args['plugin_conflict_error']:
        pm = PluginManager(repo.path)
        for plugin, version in pm.list():
            local_changes = pm.local_modifications(plugin)
            if local_changes:
                yield _("{x} Plugin '{plugin}' has local modifications:").format(
                    plugin=plugin,
                    x=red("✘"),
                )
                for path, actual_checksum, should_checksum in local_changes:
                    yield _("\t{path} ({actual_checksum}) should be {should_checksum}").format(
                        actual_checksum=actual_checksum,
                        path=path,
                        should_checksum=should_checksum,
                    )
                yield 1
                raise StopIteration()
            else:
                yield _("{x} Plugin '{plugin}' has no local modifications.").format(
                    plugin=plugin,
                    x=green("✓"),
                )

    if not args['target']:
        repo.hooks.test(repo)
