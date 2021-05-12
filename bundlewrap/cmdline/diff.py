from copy import copy
from difflib import unified_diff
from sys import exit

from ..exceptions import NoSuchItem
from ..metadata import metadata_to_json
from ..repo import Repository
from ..utils.cmdline import get_target_nodes
from ..utils.dicts import diff_dict, dict_to_text
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


def diff_metadata(node_a, node_b):
    node_a_metadata = metadata_to_json(node_a.metadata).splitlines()
    node_b_metadata = metadata_to_json(node_b.metadata).splitlines()
    io.stdout("\n".join(unified_diff(
        node_a_metadata,
        node_b_metadata,
        fromfile=node_a.name,
        tofile=node_b.name,
        lineterm='',
    )))


def diff_item(node_a, node_b, item):
    item_a = node_a.get_item(item)
    item_a_dict = item_a.display_on_create(item_a.cdict().copy())
    item_b = node_b.get_item(item)
    item_b_dict = item_b.display_on_create(item_b.cdict().copy())
    io.stdout(diff_dict(item_a_dict, item_b_dict))


def diff_node(node_a, node_b):
    node_a_hashes = sorted(
        ["{}\t{}".format(i, h) for i, h in node_a.cdict.items()]
    )
    node_b_hashes = sorted(
        ["{}\t{}".format(i, h) for i, h in node_b.cdict.items()]
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
    node_before_metadata = metadata_to_json(node.metadata).splitlines()

    for intermission in intermissions:
        intermission()

    after_repo = Repository(repo.path)
    node_after = after_repo.get_node(node.name)
    node_after_metadata = metadata_to_json(node_after.metadata).splitlines()
    io.stdout("\n".join(unified_diff(
        node_before_metadata,
        node_after_metadata,
        fromfile=_("before"),
        tofile=_("after"),
        lineterm='',
    )))

    for epilogue in epilogues:
        epilogue()


def hooked_diff_metadata_multiple_nodes(repo, nodes, intermissions, epilogues):
    nodes_metadata_before = {}
    for node in nodes:
        if QUIT_EVENT.is_set():
            exit(1)
        nodes_metadata_before[node.name] = node.metadata_hash()

    for intermission in intermissions:
        intermission()

    after_repo = Repository(repo.path)
    nodes_metadata_after = {}
    for node_name in nodes_metadata_before:
        if QUIT_EVENT.is_set():
            exit(1)
        nodes_metadata_after[node_name] = \
            after_repo.get_node(node_name).metadata_hash()

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

    for epilogue in epilogues:
        epilogue()


def hooked_diff_single_item(repo, node, item, intermissions, epilogues):
    try:
        item_before = node.get_item(item)
    except NoSuchItem:
        item_before = None
        item_before_dict = None
    else:
        item_before_dict = item_before.cdict()
        if item_before_dict:
            item_before_dict = item_before.display_on_create(copy(item_before_dict))

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
        item_after_dict = item_after.cdict()
        if item_after_dict:
            item_after_dict = item_after.display_on_create(copy(item_after_dict))

    for epilogue in epilogues:
        epilogue()

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
    item_hashes_before = {
        item.id: item.hash() for item in node.items
        if item.ITEM_TYPE_NAME != 'action'
    }

    for intermission in intermissions:
        intermission()

    after_repo = Repository(repo.path)
    after_node = after_repo.get_node(node.name)

    item_hashes_after = {
        item.id: item.hash() for item in after_node.items
        if item.ITEM_TYPE_NAME != 'action'
    }

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
        nodes_config_before[node.name] = node.hash()

    for intermission in intermissions:
        intermission()

    after_repo = Repository(repo.path)
    nodes_config_after = {}
    for node_name in nodes_config_before:
        if QUIT_EVENT.is_set():
            exit(1)
        nodes_config_after[node_name] = \
            after_repo.get_node(node_name).hash()

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

    for epilogue in epilogues:
        epilogue()


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
