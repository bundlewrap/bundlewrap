from copy import copy
from sys import exit

from ..deps import DummyItem
from ..exceptions import FaultUnavailable, ItemDependencyLoop
from ..itemqueue import ItemTestQueue
from ..metadata import check_for_metadata_conflicts, metadata_to_json
from ..repo import Repository
from ..utils.cmdline import count_items, get_target_nodes
from ..utils.dicts import diff_value_text
from ..utils.plot import explain_item_dependency_loop
from ..utils.text import bold, green, mark_for_translation as _, red, yellow
from ..utils.ui import io, QUIT_EVENT


def test_items(nodes, ignore_missing_faults, quiet):
    io.progress_set_total(count_items(nodes))
    for node in nodes:
        if QUIT_EVENT.is_set():
            break
        if not node.items:
            io.stdout(_("{x} {node}  has no items").format(node=bold(node.name), x=yellow("!")))
            continue
        item_queue = ItemTestQueue(node.items, node.os, node.os_version)
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
                if not quiet:
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
    io.progress_set_total(0)


def test_subgroup_loops(repo, quiet):
    checked_groups = []
    for group in repo.groups:
        if QUIT_EVENT.is_set():
            break
        if group in checked_groups:
            continue
        with io.job(_("{group}  checking for subgroup loops").format(group=bold(group.name))):
            checked_groups.extend(group.subgroups)  # the subgroups property has the check built in
        if not quiet:
            io.stdout(_("{x} {group}  has no subgroup loops").format(
                x=green("✓"),
                group=bold(group.name),
            ))


def test_metadata_conflicts(node, quiet):
    with io.job(_("{node}  checking for metadata conflicts").format(node=bold(node.name))):
        check_for_metadata_conflicts(node)
    if not quiet:
        io.stdout(_("{x} {node}  has no metadata conflicts").format(
            x=green("✓"),
            node=bold(node.name),
        ))


def test_orphaned_bundles(repo):
    orphaned_bundles = set(repo.bundle_names)
    for node in repo.nodes:
        if QUIT_EVENT.is_set():
            break
        for bundle in node.bundles:
            if QUIT_EVENT.is_set():
                break
            orphaned_bundles.discard(bundle.name)
    for bundle in sorted(orphaned_bundles):
        io.stderr(_("{x} {bundle}  is an unused bundle").format(
            bundle=bold(bundle),
            x=red("✘"),
        ))
    if orphaned_bundles:
        exit(1)


def test_empty_groups(repo):
    empty_groups = set()
    for group in repo.groups:
        if QUIT_EVENT.is_set():
            break
        if not group.nodes:
            empty_groups.add(group)
    for group in sorted(empty_groups):
        io.stderr(_("{x} {group}  is an empty group").format(
            group=bold(group),
            x=red("✘"),
        ))
    if empty_groups:
        exit(1)


def test_determinism_config(repo, nodes, iterations, quiet):
    """
    Generate configuration a couple of times for every node and see if
    anything changes between iterations
    """
    hashes = {}
    io.progress_set_total(len(nodes) * iterations)
    for i in range(iterations):
        if QUIT_EVENT.is_set():
            break
        if i == 0:
            # optimization: for the first iteration, just use the repo
            # we already have
            iteration_repo = repo
        else:
            iteration_repo = Repository(repo.path)
        iteration_nodes = [iteration_repo.get_node(node.name) for node in nodes]
        for node in iteration_nodes:
            if QUIT_EVENT.is_set():
                break
            with io.job(_("{node}  generating configuration ({i}/{n})").format(
                i=i + 1,
                n=iterations,
                node=bold(node.name),
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
    io.progress_set_total(0)
    if not quiet:
        io.stdout(_("{x} Configuration remained the same after being generated {n} times").format(
            n=iterations,
            x=green("✓"),
        ))


def test_determinism_metadata(repo, nodes, iterations, quiet):
    """
    Generate metadata a couple of times for every node and see if
    anything changes between iterations
    """
    hashes = {}
    metadata = {}
    io.progress_set_total(len(nodes) * iterations)
    for i in range(iterations):
        if QUIT_EVENT.is_set():
            break
        if i == 0:
            # optimization: for the first iteration, just use the repo
            # we already have
            iteration_repo = repo
        else:
            iteration_repo = Repository(repo.path)
        iteration_nodes = [iteration_repo.get_node(node.name) for node in nodes]
        for node in iteration_nodes:
            if QUIT_EVENT.is_set():
                break
            with io.job(_("{node}  generating metadata ({i}/{n})").format(
                i=i + 1,
                n=iterations,
                node=bold(node.name),
            )):
                metadata.setdefault(node.name, node.metadata)
                result = node.metadata_hash()
            hashes.setdefault(node.name, result)
            if hashes[node.name] != result:
                io.stderr(_(
                    "{x} Metadata for node {node} changed when generated repeatedly"
                ).format(node=bold(node.name), x=red("✘")))
                previous_json = metadata_to_json(metadata[node.name])
                current_json = metadata_to_json(node.metadata)
                io.stderr(diff_value_text("", previous_json, current_json))
                exit(1)
            io.progress_advance()
    io.progress_set_total(0)
    if not quiet:
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
        args['metadata_conflicts'] or
        args['orphaned_bundles'] or
        args['empty_groups'] or
        args['subgroup_loops']
    )
    if args['targets']:
        nodes = get_target_nodes(repo, args['targets'])
        if not options_selected:
            args['hooks_node'] = True
            args['items'] = True
            args['metadata_conflicts'] = True
            args['metadata_keys'] = True
    else:
        nodes = copy(list(repo.nodes))
        if not options_selected:
            args['hooks_node'] = True
            args['hooks_repo'] = True
            args['items'] = True
            args['metadata_conflicts'] = True
            args['metadata_keys'] = True
            args['subgroup_loops'] = True

    if args['subgroup_loops'] and not QUIT_EVENT.is_set():
        test_subgroup_loops(repo, args['quiet'])

    if args['empty_groups'] and not QUIT_EVENT.is_set():
        test_empty_groups(repo)

    if args['orphaned_bundles'] and not QUIT_EVENT.is_set():
        test_orphaned_bundles(repo)

    if args['metadata_conflicts'] and not QUIT_EVENT.is_set():
        io.progress_set_total(len(nodes))
        for node in nodes:
            if QUIT_EVENT.is_set():
                break
            test_metadata_conflicts(node, args['quiet'])
            io.progress_advance()
        io.progress_set_total(0)

    if args['items']:
        test_items(nodes, args['ignore_missing_faults'], args['quiet'])

    if args['determinism_metadata'] > 1 and not QUIT_EVENT.is_set():
        test_determinism_metadata(repo, nodes, args['determinism_metadata'], args['quiet'])

    if args['determinism_config'] > 1 and not QUIT_EVENT.is_set():
        test_determinism_config(repo, nodes, args['determinism_config'], args['quiet'])

    if args['hooks_node'] and not QUIT_EVENT.is_set():
        io.progress_set_total(len(nodes))
        for node in nodes:
            if QUIT_EVENT.is_set():
                break
            repo.hooks.test_node(repo, node)
            io.progress_advance()
        io.progress_set_total(0)

    if args['hooks_repo'] and not QUIT_EVENT.is_set():
        repo.hooks.test(repo)
