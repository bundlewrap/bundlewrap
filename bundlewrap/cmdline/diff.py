from difflib import unified_diff

from ..items.files import DIFF_MAX_FILE_SIZE
from ..metadata import metadata_to_json
from ..repo import Repository
from ..utils.cmdline import get_target_nodes
from ..utils.dicts import diff_keys, diff_value
from ..utils.scm import get_git_branch, get_git_rev, set_git_rev
from ..utils.text import force_text, mark_for_translation as _, red, blue, yellow
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
    item_a_dict = item_a.cdict()
    item_b = node_b.get_item(item)
    item_b_dict = item_b.cdict()

    if (
        item.startswith("file:")
        and item_a.attributes['content_type'] not in ('base64', 'binary')
        and item_b.attributes['content_type'] not in ('base64', 'binary')
        and len(item_a.content) < DIFF_MAX_FILE_SIZE
        and len(item_b.content) < DIFF_MAX_FILE_SIZE
    ):
        del item_a_dict['content_hash']
        del item_b_dict['content_hash']
        item_a_dict['content'] = item_a.content
        item_b_dict['content'] = item_b.content

    relevant_keys = diff_keys(item_a_dict, item_b_dict)
    io.stdout("\n".join(
        diff_value(key, item_a_dict[key], item_b_dict[key])
        for key in relevant_keys
    ))


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
            "{x} Switching to git rev: {rev}"
        ).format(
            rev=rev,
            x=yellow("i"),
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
    item_before = node.get_item(item)
    item_before_dict = item_before.cdict()
    item_before_diffable = False
    item_before_content = None

    if (
        item.startswith("file:")
        and item_before.attributes['content_type'] not in ('base64', 'binary')
        and len(item_before.content) < DIFF_MAX_FILE_SIZE
    ):
        item_before_diffable = True
        item_before_content = item_before.content

    for intermission in intermissions:
        intermission()

    repo_after = Repository(repo.path)
    node_after = repo_after.get_node(node.name)
    item_after = node_after.get_item(item)
    item_after_dict = item_after.cdict()

    if (
        item.startswith("file:")
        and item_before_diffable
        and item_after.attributes['content_type'] not in ('base64', 'binary')
        and len(item_after.content) < DIFF_MAX_FILE_SIZE
    ):
        del item_before_dict['content_hash']
        del item_after_dict['content_hash']
        item_before_dict['content'] = item_before_content
        item_after_dict['content'] = item_after.content

    relevant_keys = diff_keys(item_before_dict, item_after_dict)
    io.stdout(item_before.ask(item_after_dict, item_before_dict, relevant_keys))

    for epilogue in epilogues:
        epilogue()


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
