# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from copy import copy
from sys import exit

from ..deps import DummyItem
from ..exceptions import FaultUnavailable, ItemDependencyLoop
from ..itemqueue import ItemTestQueue
from ..metadata import check_for_unsolvable_metadata_key_conflicts
from ..plugins import PluginManager
from ..repo import Repository
from ..utils.cmdline import count_items, get_target_nodes
from ..utils.plot import explain_item_dependency_loop
from ..utils.text import bold, green, mark_for_translation as _, red, yellow
from ..utils.ui import io, QUIT_EVENT


def test_items(nodes, ignore_missing_faults):
    with io.job(_("  counting items...")):
        io.progress_set_total(count_items(nodes))
    for node in nodes:
        if QUIT_EVENT.is_set():
            break
        if not node.items:
            io.stdout(_("{x} {node}  has no items").format(node=bold(node.name), x=yellow("!")))
            continue
        item_queue = ItemTestQueue(node.items)
        while not QUIT_EVENT.is_set():
            try:
                item = item_queue.pop()
            except IndexError:  # no items left
                break
            if isinstance(item, DummyItem):
                continue
            try:
                item._test()
            except FaultUnavailable:
                if ignore_missing_faults:
                    io.progress_advance()
                    io.stderr(_("{x} {node}  {bundle}  {item}  ({msg})").format(
                        bundle=bold(item.bundle.name),
                        item=item.id,
                        msg=yellow(_("Fault unavailable")),
                        node=bold(node.name),
                        x=yellow("»"),
                    ))
                else:
                    io.stderr(_("{x} {node}  {bundle}  {item}  missing Fault:").format(
                        bundle=bold(item.bundle.name),
                        item=item.id,
                        node=bold(node.name),
                        x=red("!"),
                    ))
                    raise
            except Exception:
                io.stderr(_("{x} {node}  {bundle}  {item}").format(
                    bundle=bold(item.bundle.name),
                    item=item.id,
                    node=bold(node.name),
                    x=red("!"),
                ))
                raise
            else:
                if item.id.count(":") < 2:
                    # don't count canned actions
                    io.progress_advance()
                io.stdout("{x} {node}  {bundle}  {item}".format(
                    bundle=bold(item.bundle.name),
                    item=item.id,
                    node=bold(node.name),
                    x=green("✓"),
                ))
        if item_queue.items_with_deps and not QUIT_EVENT.is_set():
            exception = ItemDependencyLoop(item_queue.items_with_deps)
            for line in explain_item_dependency_loop(exception, node.name):
                io.stderr(line)
            exit(1)


def test_subgroup_loops(repo):
    checked_groups = []
    for group in repo.groups:
        if group in checked_groups:
            continue
        with io.job(_("  {group}  checking for subgroup loops...").format(group=group.name)):
            checked_groups.extend(group.subgroups)  # the subgroups property has the check built in
        io.stdout(_("{x} {group}  has no subgroup loops").format(
            x=green("✓"),
            group=bold(group.name),
        ))


def test_metadata_collisions(node):
    with io.job(_("  {node}  checking for metadata collisions...").format(node=node.name)):
        check_for_unsolvable_metadata_key_conflicts(node)
    io.stdout(_("{x} {node}  has no metadata collisions").format(
        x=green("✓"),
        node=bold(node.name),
    ))


def test_orphaned_bundles(repo):
    orphaned_bundles = set(repo.bundle_names)
    for node in repo.nodes:
        for bundle in node.bundles:
            orphaned_bundles.discard(bundle.name)
    for bundle in sorted(orphaned_bundles):
        io.stderr(_("{x} {bundle}  is an unused bundle").format(
            bundle=bold(bundle),
            x=red("✘"),
        ))
    if orphaned_bundles:
        exit(1)


def test_orphaned_groups(repo):
    orphaned_groups = set()
    for group in repo.groups:
        if not group.nodes:
            orphaned_groups.append(group)
    for bundle in sorted(orphaned_groups):
        io.stderr(_("{x} {group}  is an empty group").format(
            group=bold(group),
            x=red("✘"),
        ))
    if orphaned_groups:
        exit(1)


def test_plugin_conflicts(repo):
    pm = PluginManager(repo.path)
    for plugin, version in pm.list():
        local_changes = pm.local_modifications(plugin)
        if local_changes:
            io.stderr(_("{x}  Plugin '{plugin}' has local modifications:").format(
                plugin=plugin,
                x=red("✘"),
            ))
            for path, actual_checksum, should_checksum in local_changes:
                io.stderr(_("\t{path} ({actual_checksum}) should be {should_checksum}").format(
                    actual_checksum=actual_checksum,
                    path=path,
                    should_checksum=should_checksum,
                ))
            exit(1)
        else:
            io.stdout(_("{x}  Plugin '{plugin}' has no local modifications.").format(
                plugin=plugin,
                x=green("✓"),
            ))


def test_determinism_config(repo, nodes, iterations):
    """
    Generate configuration a couple of times for every node and see if
    anything changes between iterations
    """
    hashes = {}
    io.progress_set_total(len(nodes) * iterations)
    for i in range(iterations):
        if i == 0:
            # optimization: for the first iteration, just use the repo
            # we already have
            iteration_repo = repo
        else:
            iteration_repo = Repository(repo.path)
        iteration_nodes = [iteration_repo.get_node(node.name) for node in nodes]
        for node in iteration_nodes:
            with io.job(_("  {node}  generating configuration ({i}/{n})...").format(
                i=i + 1,
                n=iterations,
                node=node.name,
            )):
                result = node.hash()
            hashes.setdefault(node.name, result)
            if hashes[node.name] != result:
                io.stderr(_(
                    "{x} Configuration for node {node} changed when generated repeatedly "
                    "(use `bw hash -d {node}` to debug)"
                ).format(node=node.name, x=red("✘")))
                exit(1)
            io.progress_advance()
    io.stdout(_("{x} Configuration remained the same after being generated {n} times").format(
        n=iterations,
        x=green("✓"),
    ))


def test_determinism_metadata(repo, nodes, iterations):
    """
    Generate metadata a couple of times for every node and see if
    anything changes between iterations
    """
    hashes = {}
    io.progress_set_total(len(nodes) * iterations)
    for i in range(iterations):
        if i == 0:
            # optimization: for the first iteration, just use the repo
            # we already have
            iteration_repo = repo
        else:
            iteration_repo = Repository(repo.path)
        iteration_nodes = [iteration_repo.get_node(node.name) for node in nodes]
        for node in iteration_nodes:
            with io.job(_("  {node}  generating metadata ({i}/{n})... ").format(
                i=i + 1,
                n=iterations,
                node=node.name,
            )):
                result = node.metadata_hash()
            hashes.setdefault(node.name, result)
            if hashes[node.name] != result:
                io.stderr(_(
                    "{x} Metadata for node {node} changed when generated repeatedly "
                    "(use `bw hash -d {node}` to debug)"
                ).format(node=node.name, x=red("✘")))
                exit(1)
            io.progress_advance()
    io.stdout(_("{x} Metadata remained the same after being generated {n} times").format(
        n=iterations,
        x=green("✓"),
    ))


def bw_test(repo, args):
    options_selected = (
        args['determinism_config'] > 1 or
        args['determinism_metadata'] > 1 or
        args['hooks_node'] or
        args['hooks_repo'] or
        args['items'] or
        args['metadata_collisions'] or
        args['orphaned_bundles'] or
        args['orphaned_groups'] or
        args['plugin_conflicts'] or
        args['subgroup_loops']
    )
    if args['target']:
        nodes = get_target_nodes(repo, args['target'], adhoc_nodes=args['adhoc_nodes'])
        if not options_selected:
            args['hooks_node'] = True
            args['items'] = True
            args['metadata_collisions'] = True
    else:
        nodes = copy(list(repo.nodes))
        if not options_selected:
            args['hooks_node'] = True
            args['hooks_repo'] = True
            args['items'] = True
            args['metadata_collisions'] = True
            args['subgroup_loops'] = True

    if args['plugin_conflicts'] and not QUIT_EVENT.is_set():
        test_plugin_conflicts(repo)

    if args['subgroup_loops'] and not QUIT_EVENT.is_set():
        test_subgroup_loops(repo)

    if args['orphaned_groups'] and not QUIT_EVENT.is_set():
        test_orphaned_groups(repo)

    if args['orphaned_bundles'] and not QUIT_EVENT.is_set():
        test_orphaned_bundles(repo)

    if args['metadata_collisions'] and not QUIT_EVENT.is_set():
        io.progress_set_total(len(nodes))
        for node in nodes:
            test_metadata_collisions(node)
            io.progress_advance()

    if args['items']:
        test_items(nodes, args['ignore_missing_faults'])

    if args['determinism_metadata'] > 1 and not QUIT_EVENT.is_set():
        test_determinism_metadata(repo, nodes, args['determinism_metadata'])

    if args['determinism_config'] > 1 and not QUIT_EVENT.is_set():
        test_determinism_config(repo, nodes, args['determinism_config'])

    if args['hooks_node'] and not QUIT_EVENT.is_set():
        io.progress_set_total(len(nodes))
        for node in nodes:
            repo.hooks.test_node(repo, node)
            io.progress_advance()

    if args['hooks_repo'] and not QUIT_EVENT.is_set():
        repo.hooks.test(repo)
