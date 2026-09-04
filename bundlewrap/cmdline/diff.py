from copy import copy
from difflib import unified_diff
from sys import exit

from ..exceptions import FaultUnavailable, NoSuchItem
from ..metadata import metadata_to_json
from ..repo import Repository
from ..utils.cmdline import get_target_nodes
from ..utils.dicts import diff_dict, dict_to_text, hash_state_dict
from ..utils.scm import get_git_branch, get_git_rev, set_git_rev
from ..utils.text import (
    bold,
    force_text,
    green,
    mark_for_translation as _,
    prefix_lines,
    red,
    blue,
    yellow,
)
from ..utils.ui import io, QUIT_EVENT

from subprocess import check_call


def _report_fault_unavailable(item):
    io.stderr(_("{x} {node}  {bundle}  {item}  ({msg})").format(
        bundle=bold(item.bundle.name),
        item=item.id,
        msg=yellow(_("Fault unavailable")),
        node=bold(item.node.name),
        x=yellow("»"),
    ))


def _metadata_lines_pair(node_a, node_b):
    """
    Returns the metadata of both nodes as JSON lines. If a Fault cannot
    be resolved on either side, *both* sides are rendered with
    unresolved Faults so the diff doesn't show spurious differences.
    """
    try:
        return (
            metadata_to_json(node_a.metadata).splitlines(),
            metadata_to_json(node_b.metadata).splitlines(),
        )
    except FaultUnavailable:
        io.stderr(_("{x} Fault unavailable, showing unresolved Faults").format(
            x=yellow("»"),
        ))
        return (
            metadata_to_json(node_a.metadata, resolve_faults=False).splitlines(),
            metadata_to_json(node_b.metadata, resolve_faults=False).splitlines(),
        )


def _metadata_hashes(node):
    """
    Returns (hash_resolved, hash_unresolved) for the node's metadata.
    hash_resolved is None if a Fault is unavailable.
    """
    hash_unresolved = hash_state_dict(metadata_to_json(node.metadata, resolve_faults=False))
    try:
        return (node.metadata_hash(), hash_unresolved)
    except FaultUnavailable:
        io.stderr(_("{x} {node}  Fault unavailable, hashing unresolved Faults").format(
            node=bold(node.name),
            x=yellow("»"),
        ))
        return (None, hash_unresolved)


def _pick_comparable_hashes(before, after):
    """
    Given two dicts of {node_name: (hash_resolved, hash_unresolved)},
    return two dicts of {node_name: hash} using the resolved hash only
    where it is available on both sides.
    """
    picked_before = {}
    picked_after = {}
    for node_name in before:
        resolved_before, unresolved_before = before[node_name]
        resolved_after, unresolved_after = after[node_name]
        if resolved_before is None or resolved_after is None:
            picked_before[node_name] = unresolved_before
            picked_after[node_name] = unresolved_after
        else:
            picked_before[node_name] = resolved_before
            picked_after[node_name] = resolved_after
    return picked_before, picked_after


def _item_display_dict(item):
    """
    Returns the expected_state of an item prepared for display, or None
    for items that are to be deleted. Raises FaultUnavailable.
    """
    expected_state = item.cached_expected_state
    if expected_state is None:
        return None
    return item.display_on_create(copy(expected_state))


def diff_metadata(node_a, node_b):
    node_a_metadata, node_b_metadata = _metadata_lines_pair(node_a, node_b)
    io.stdout("\n".join(unified_diff(
        node_a_metadata,
        node_b_metadata,
        fromfile=node_a.name,
        tofile=node_b.name,
        lineterm='',
    )))


def diff_item(node_a, node_b, item):
    dicts = []
    for node in (node_a, node_b):
        node_item = node.get_item(item)
        try:
            dicts.append(_item_display_dict(node_item) or {})
        except FaultUnavailable:
            _report_fault_unavailable(node_item)
            exit(1)
    io.stdout(diff_dict(*dicts))


def diff_node(node_a, node_b):
    node_a_hashes = sorted(
        ["{}\t{}".format(i, h) for i, h in node_a.expected_state.items()]
    )
    node_b_hashes = sorted(
        ["{}\t{}".format(i, h) for i, h in node_b.expected_state.items()]
    )
    io.stdout("\n".join(
        filter(
            lambda line: line.startswith("+") or line.startswith("-"),
            unified_diff(
                node_a_hashes,
                node_b_hashes,
                fromfile=node_a.name,
                tofile=node_b.name,
                lineterm='',
                n=0,
            ),
        ),
    ))


def command_closure(command):
    def run_it():
        io.stderr(_(
            "{x} Running: {command}"
        ).format(
            command=command,
            x=yellow("i"),
        ))
        check_call(command, shell=True)

    return run_it


def git_checkout_closure(rev, detach=False):
    def run_it():
        io.stderr(_(
            "{x} {git}  switching to rev: {rev}"
        ).format(
            x=blue("i"),
            git=bold("git"),
            rev=rev,
        ))
        set_git_rev(rev, detach=detach)

    return run_it


def hooked_diff_metadata_single_node(repo, node, intermissions, epilogues):
    node.metadata.get(tuple())  # build metadata before the repo changes

    try:
        for intermission in intermissions:
            intermission()

        after_repo = Repository(repo.path)
        node_after = after_repo.get_node(node.name)
        node_before_metadata, node_after_metadata = _metadata_lines_pair(node, node_after)
    finally:
        for epilogue in epilogues:
            epilogue()

    io.stdout("\n".join(unified_diff(
        node_before_metadata,
        node_after_metadata,
        fromfile=_("before"),
        tofile=_("after"),
        lineterm='',
    )))


def hooked_diff_metadata_multiple_nodes(repo, nodes, intermissions, epilogues):
    nodes_metadata_before = {}
    for node in nodes:
        if QUIT_EVENT.is_set():
            exit(1)
        nodes_metadata_before[node.name] = _metadata_hashes(node)

    try:
        for intermission in intermissions:
            intermission()

        after_repo = Repository(repo.path)
        nodes_metadata_after = {}
        for node_name in nodes_metadata_before:
            if QUIT_EVENT.is_set():
                exit(1)
            nodes_metadata_after[node_name] = \
                _metadata_hashes(after_repo.get_node(node_name))
    finally:
        for epilogue in epilogues:
            epilogue()

    nodes_metadata_before, nodes_metadata_after = _pick_comparable_hashes(
        nodes_metadata_before,
        nodes_metadata_after,
    )

    node_hashes_before = sorted(
        ["{}\t{}".format(i, h) for i, h in nodes_metadata_before.items()]
    )
    node_hashes_after = sorted(
        ["{}\t{}".format(i, h) for i, h in nodes_metadata_after.items()]
    )
    io.stdout("\n".join(
        filter(
            lambda line: line.startswith("+") or line.startswith("-"),
            unified_diff(
                node_hashes_before,
                node_hashes_after,
                fromfile=_("before"),
                tofile=_("after"),
                lineterm='',
                n=0,
            ),
        ),
    ))


def hooked_diff_single_item(repo, node, item, intermissions, epilogues):
    fault_unavailable = False
    try:
        item_before = node.get_item(item)
    except NoSuchItem:
        item_before = None
        item_before_dict = None
    else:
        try:
            item_before_dict = _item_display_dict(item_before)
        except FaultUnavailable:
            _report_fault_unavailable(item_before)
            fault_unavailable = True
            item_before_dict = None

    try:
        for intermission in intermissions:
            intermission()

        repo_after = Repository(repo.path)
        node_after = repo_after.get_node(node.name)
        try:
            item_after = node_after.get_item(item)
        except NoSuchItem:
            item_after = None
            item_after_dict = None
        else:
            try:
                item_after_dict = _item_display_dict(item_after)
            except FaultUnavailable:
                _report_fault_unavailable(item_after)
                fault_unavailable = True
                item_after_dict = None
    finally:
        for epilogue in epilogues:
            epilogue()

    if fault_unavailable:
        # showing only one side would look like the item was added or removed
        exit(1)

    if item_before is None and item_after is None:
        io.stderr(_("{x} {node}  {item}  not found anywhere").format(
            x=bold(red("!")),
            node=bold(node.name),
            item=bold(item),
        ))
        exit(1)
    if item_before is None:
        io.stdout(_("{x} {node}  {item}  not found previously").format(
            x=bold(yellow("!")),
            node=bold(node.name),
            item=bold(item),
        ))
    if item_before_dict and item_after_dict:
        io.stdout(
            f"{bold(blue('i'))} {bold(node.name)}  {bold(item_before.bundle.name)}  {item}\n" +
            prefix_lines(
                "\n" + diff_dict(item_before_dict, item_after_dict),
                yellow("│ "),
            ).rstrip("\n") +
            "\n" + yellow("╵")
        )
    elif item_before_dict:
        io.stdout(
            f"{bold(red('-'))} {bold(node.name)}  {bold(item_before.bundle.name)}  {item}\n" +
            prefix_lines(
                "\n" + dict_to_text(item_before_dict, value_color=red),
                red("│ "),
            ).rstrip("\n") +
            "\n" + red("╵")
        )
    elif item_after_dict:
        io.stdout(
            f"{bold(green('+'))} {bold(node.name)}  {bold(item_after.bundle.name)}  {item}\n" +
            prefix_lines(
                "\n" + dict_to_text(item_after_dict),
                green("│ "),
            ).rstrip("\n") +
            "\n" + green("╵")
        )
    if item_after is None:
        io.stdout(_("{x} {node}  {item}  not found after").format(
            x=bold(yellow("!")),
            node=bold(node.name),
            item=bold(item),
        ))


def hooked_diff_config_single_node(repo, node, intermissions, epilogues):
    item_hashes_before = node.expected_state

    try:
        for intermission in intermissions:
            intermission()

        after_repo = Repository(repo.path)
        after_node = after_repo.get_node(node.name)
        item_hashes_after = after_node.expected_state
    finally:
        for epilogue in epilogues:
            epilogue()

    item_hashes_before = sorted(
        ["{}\t{}".format(i, h) for i, h in item_hashes_before.items()]
    )
    item_hashes_after = sorted(
        ["{}\t{}".format(i, h) for i, h in item_hashes_after.items()]
    )
    io.stdout("\n".join(
        filter(
            lambda line: line.startswith("+") or line.startswith("-"),
            unified_diff(
                item_hashes_before,
                item_hashes_after,
                fromfile=_("before"),
                tofile=_("after"),
                lineterm='',
                n=0,
            ),
        ),
    ))


def hooked_diff_config_multiple_nodes(repo, nodes, intermissions, epilogues):
    nodes_config_before = {}
    for node in nodes:
        if QUIT_EVENT.is_set():
            exit(1)
        nodes_config_before[node.name] = hash_state_dict(node.expected_state)

    try:
        for intermission in intermissions:
            intermission()

        after_repo = Repository(repo.path)
        nodes_config_after = {}
        for node_name in nodes_config_before:
            if QUIT_EVENT.is_set():
                exit(1)
            nodes_config_after[node_name] = \
                hash_state_dict(after_repo.get_node(node_name).expected_state)
    finally:
        for epilogue in epilogues:
            epilogue()

    node_hashes_before = sorted(
        ["{}\t{}".format(i, h) for i, h in nodes_config_before.items()]
    )
    node_hashes_after = sorted(
        ["{}\t{}".format(i, h) for i, h in nodes_config_after.items()]
    )
    io.stdout("\n".join(
        filter(
            lambda line: line.startswith("+") or line.startswith("-"),
            unified_diff(
                node_hashes_before,
                node_hashes_after,
                fromfile=_("before"),
                tofile=_("after"),
                lineterm='',
                n=0,
            ),
        ),
    ))


def bw_diff(repo, args):
    if args['metadata'] and args['item']:
        io.stderr(_(
            "{x} Cannot compare metadata and items at the same time"
        ).format(x=red("!!!")))
        exit(1)

    target_nodes = sorted(get_target_nodes(repo, args['targets']))

    if args['branch'] or args['cmd_change'] or args['cmd_reset'] or args['prompt']:
        intermissions = []
        epilogues = []
        if args['branch']:
            original_rev = force_text(get_git_branch() or get_git_rev())
            intermissions.append(git_checkout_closure(force_text(args['branch']), detach=True))
        if args['cmd_change']:
            intermissions.append(command_closure(args['cmd_change']))
        if args['cmd_reset']:
            epilogues.append(command_closure(args['cmd_reset']))
        if args['branch']:
            epilogues.append(git_checkout_closure(original_rev, detach=False))

        if args['metadata']:
            if len(target_nodes) == 1:
                def intermission():
                    io.stdout(_("{x} Took a snapshot of that node's metadata.").format(x=blue("i")))
                    io.stdout(_("{x} You may now make changes to your repo.").format(x=blue("i")))
                    if not io.ask(_("{x} Ready to proceed? (n to cancel)").format(x=blue("?")), True):
                        exit(1)
                if args['prompt']:
                    intermissions.append(intermission)
                hooked_diff_metadata_single_node(repo, target_nodes[0], intermissions, epilogues)
            else:
                def intermission():
                    io.stdout(_("{x} Took a snapshot of those nodes' metadata.").format(x=blue("i")))
                    io.stdout(_("{x} You may now make changes to your repo.").format(x=blue("i")))
                    if not io.ask(_("{x} Ready to proceed? (n to cancel)").format(x=blue("?")), True):
                        exit(1)
                if args['prompt']:
                    intermissions.append(intermission)
                hooked_diff_metadata_multiple_nodes(repo, target_nodes, intermissions, epilogues)
        elif args['item']:
            if len(target_nodes) != 1:
                io.stderr(_(
                    "{x} Select exactly one node to compare item"
                ).format(x=red("!!!")))
                exit(1)

            def intermission():
                io.stdout(_("{x} Took a snapshot of that item.").format(x=blue("i")))
                io.stdout(_("{x} You may now make changes to your repo.").format(x=blue("i")))
                if not io.ask(_("{x} Ready to proceed? (n to cancel)").format(x=blue("?")), True):
                    exit(1)
            if args['prompt']:
                intermissions.append(intermission)
            hooked_diff_single_item(repo, target_nodes[0], args['item'], intermissions, epilogues)
        elif len(target_nodes) == 1:
            def intermission():
                io.stdout(_("{x} Took a snapshot of that node.").format(x=blue("i")))
                io.stdout(_("{x} You may now make changes to your repo.").format(x=blue("i")))
                if not io.ask(_("{x} Ready to proceed? (n to cancel)").format(x=blue("?")), True):
                    exit(1)
            if args['prompt']:
                intermissions.append(intermission)
            hooked_diff_config_single_node(repo, target_nodes[0], intermissions, epilogues)
        else:
            def intermission():
                io.stdout(_("{x} Took a snapshot of those nodes.").format(x=blue("i")))
                io.stdout(_("{x} You may now make changes to your repo.").format(x=blue("i")))
                if not io.ask(_("{x} Ready to proceed? (n to cancel)").format(x=blue("?")), True):
                    exit(1)
            if args['prompt']:
                intermissions.append(intermission)
            hooked_diff_config_multiple_nodes(repo, target_nodes, intermissions, epilogues)
    else:
        if len(target_nodes) != 2:
            io.stderr(_(
                "{x} Exactly two nodes must be selected"
            ).format(x=red("!!!")))
            exit(1)
        node_a, node_b = target_nodes

        if args['metadata']:
            diff_metadata(node_a, node_b)
        elif args['item']:
            diff_item(node_a, node_b, args['item'])
        else:
            diff_node(node_a, node_b)
