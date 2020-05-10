from difflib import unified_diff

from ..items.files import DIFF_MAX_FILE_SIZE
from ..metadata import metadata_to_json
from ..repo import Repository
from ..utils.cmdline import get_target_nodes
from ..utils.dicts import diff_keys
from ..utils.text import mark_for_translation as _, red, blue
from ..utils.ui import io, QUIT_EVENT


def diff_metadata(node_a, node_b):
    node_a_metadata = metadata_to_json(node_a.metadata).splitlines()
    node_b_metadata = metadata_to_json(node_b.metadata).splitlines()
    io.stdout("\n".join(unified_diff(
        node_a_metadata,
        node_b_metadata,
        fromfile=node_a.name,
        tofile=node_b.name,
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
    io.stdout(item_a.ask(item_a_dict, item_b_dict, relevant_keys))


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
                n=0,
            ),
        ),
    ))


def intermission_diff_metadata_single_node(repo, node, intermission):
    node_before_metadata = metadata_to_json(node.metadata).splitlines()

    intermission()

    after_repo = Repository(repo.path)
    node_after = after_repo.get_node(node.name)
    node_after_metadata = metadata_to_json(node_after.metadata).splitlines()
    io.stdout("\n".join(unified_diff(
        node_before_metadata,
        node_after_metadata,
        fromfile=_("before"),
        tofile=_("after"),
    )))


def intermission_diff_metadata_multiple_nodes(repo, nodes, intermission):
    nodes_metadata_before = {}
    for node in nodes:
        if QUIT_EVENT.is_set():
            exit(1)
        nodes_metadata_before[node.name] = node.metadata_hash()

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
                n=0,
            ),
        ),
    ))


def bw_diff(repo, args):
    if args['metadata'] and args['item']:
        io.stdout(_(
            "{x} Cannot compare metadata and items at the same time"
        ).format(x=red("!!!")))
        exit(1)

    target_nodes = get_target_nodes(repo, args['target'], adhoc_nodes=args['adhoc_nodes'])

    if args['branch']:
        raise NotImplementedError
    elif args['prompt']:
        if args['metadata']:
            if len(target_nodes) == 1:
                def intermission():
                    io.stdout(_("{x} Took a snapshot of that node's metadata.").format(x=blue("i")))
                    io.stdout(_("{x} You may now make changes to your repo.").format(x=blue("i")))
                    if not io.ask(_("{x} Are you done?").format(x=blue("?")), True):
                        exit(1)
                intermission_diff_metadata_single_node(repo, target_nodes[0], intermission)
            else:
                def intermission():
                    io.stdout(_("{x} Took a snapshot of those nodes' metadata.").format(x=blue("i")))
                    io.stdout(_("{x} You may now make changes to your repo.").format(x=blue("i")))
                    if not io.ask(_("{x} Are you done?").format(x=blue("?")), True):
                        exit(1)
                intermission_diff_metadata_multiple_nodes(repo, target_nodes, intermission)

        elif args['item']:
            # compare single item on single node
            raise NotImplementedError

        else:
            # compare set of entire nodes' config
            raise NotImplementedError

    else:
        if len(target_nodes) != 2:
            io.stdout(_(
                "{x} Exactly two nodes must be selected when comparing within "
                "the same branch"
            ).format(x=red("!!!")))
            exit(1)
        node_a, node_b = target_nodes

        if args['metadata']:
            diff_metadata(node_a, node_b)
        elif args['item']:
            diff_item(node_a, node_b, args['item'])
        else:
            diff_node(node_a, node_b)
