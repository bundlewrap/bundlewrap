from decimal import Decimal

from ..metadata import deepcopy_metadata, metadata_to_json
from ..utils import Fault
from ..utils.cmdline import get_node, get_target_nodes
from ..utils.dicts import delete_key_at_path, replace_key_at_path, value_at_key_path
from ..utils.table import ROW_SEPARATOR, render_table
from ..utils.text import bold, force_text, green, grey, mark_for_translation as _, red, yellow
from ..utils.ui import io, page_lines


def _color_for_source(key, source):
    if source.startswith("metadata_defaults:"):
        return grey(key)
    elif source.startswith("metadata_reactor:"):
        return green(key)
    elif source.startswith("group:"):
        return yellow(key)
    elif source.startswith("node:"):
        return red(key)
    else:
        return key


def _colorize_path(args, metadata, path, src):
    if src.startswith("metadata_defaults:") and args['hide_defaults']:
        delete_key_at_path(metadata, path)
    else:
        replace_key_at_path(
            metadata,
            path,
            _color_for_source(path[-1], src),
        )


def bw_metadata(repo, args):
    if args['table']:
        if not args['keys']:
            io.stdout(_("{x} at least one key is required with --table").format(x=red("!!!")))
            exit(1)
        target_nodes = get_target_nodes(repo, args['target'], adhoc_nodes=args['adhoc_nodes'])
        key_paths = [path.strip().split(" ") for path in " ".join(args['keys']).split(",")]
        table = [[bold(_("node"))] + [bold(" ".join(path)) for path in key_paths], ROW_SEPARATOR]
        for node in target_nodes:
            values = []
            for key_path in key_paths:
                metadata = node.metadata
                try:
                    value = value_at_key_path(metadata, key_path)
                except KeyError:
                    value = red(_("<missing>"))
                if isinstance(value, (dict, list, tuple)):
                    value = ", ".join([str(item) for item in value])
                elif isinstance(value, set):
                    value = ", ".join(sorted(value))
                elif isinstance(value, (bool, float, int, Decimal, Fault)) or value is None:
                    value = str(value)
                values.append(value)
            table.append([bold(node.name)] + values)
        page_lines(render_table(table))
    else:
        node = get_node(repo, args['target'], adhoc_nodes=args['adhoc_nodes'])
        if args['blame']:
            key_paths = [path.strip() for path in " ".join(args['keys']).split(",")]
            table = [[bold(_("path")), bold(_("source"))], ROW_SEPARATOR]
            for path, blamed in sorted(node.metadata_blame.items()):
                joined_path = " ".join(path)
                for key_path in key_paths:
                    if joined_path.startswith(key_path):
                        table.append([joined_path, ", ".join(blamed)])
                        break
            page_lines(render_table(table))
        else:
            if args['color'] or args['hide_defaults']:
                metadata = deepcopy_metadata(node.metadata)
                blame = list(node.metadata_blame.items())
                # sort descending by key path length since we will be replacing
                # the keys and can't access paths beneath replaced keys anymore
                blame.sort(key=lambda e: len(e[0]), reverse=True)
                for path, blamed in blame:
                    value = value_at_key_path(metadata, path)
                    if isinstance(value, (dict, list, tuple, set)):
                        if len(blamed) == 1:
                            _colorize_path(args, metadata, path, blamed[0])
                    else:
                        _colorize_path(args, metadata, path, blamed[-1])
            else:
                metadata = node.metadata

            for line in metadata_to_json(
                value_at_key_path(metadata, args['keys']),
            ).splitlines():
                io.stdout(force_text(line).replace("\\u001b", "\033"))
