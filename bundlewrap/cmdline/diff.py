from difflib import unified_diff

from ..items.files import DIFF_MAX_FILE_SIZE
from ..metadata import metadata_to_json
from ..utils.cmdline import get_target_nodes
from ..utils.dicts import diff_keys
from ..utils.text import mark_for_translation as _, red
from ..utils.ui import io


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
            node_a_metadata = metadata_to_json(node_a.metadata).splitlines()
            node_b_metadata = metadata_to_json(node_b.metadata).splitlines()
            io.stdout("\n".join(unified_diff(
                node_a_metadata,
                node_b_metadata,
                fromfile=node_a.name,
                tofile=node_b.name,
            )))

        elif args['item']:
            item_a = node_a.get_item(args['item'])
            item_a_dict = item_a.cdict()
            item_b = node_b.get_item(args['item'])
            item_b_dict = item_b.cdict()

            if (
                args['item'].startswith("file:")
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

        else:  # diffing entire node
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
