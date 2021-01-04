from collections import OrderedDict
from contextlib import suppress
from decimal import Decimal
from sys import version_info

from ..metadata import metadata_to_json
from ..utils import Fault, list_starts_with
from ..utils.cmdline import get_target_nodes
from ..utils.dicts import (
    delete_key_at_path,
    replace_key_at_path,
    set_key_at_path,
    value_at_key_path,
)
from ..utils.table import ROW_SEPARATOR, render_table
from ..utils.text import (
    ansi_clean,
    blue,
    bold,
    force_text,
    green,
    mark_for_translation as _,
    red,
    yellow,
)
from ..utils.ui import io, page_lines


def _color_for_source(key, source):
    if source.startswith("metadata_defaults:"):
        return blue(key)
    elif source.startswith("metadata_reactor:"):
        return green(key)
    elif source.startswith("group:"):
        return yellow(key)
    elif source.startswith("node:"):
        return red(key)
    else:
        return key


def _colorize_path(
    metadata,
    path,
    sources,
    hide_defaults,
    hide_reactors,
    hide_groups,
    hide_node,
):
    if not isinstance(value_at_key_path(metadata, path), (dict, list, tuple, set)):
        # only last source relevant for atomic types
        sources = [sources[-1]]
    sources_filtered = False
    for src in sources.copy():
        if (
            (src.startswith("metadata_defaults:") and hide_defaults) or
            (src.startswith("metadata_reactor:") and hide_reactors) or
            (src.startswith("group:") and hide_groups) or
            (src.startswith("node:") and hide_node)
        ):
            sources.remove(src)
            sources_filtered = True
    if not sources:
        delete_key_at_path(metadata, path)
        return None
    elif len(sources) == 1:
        if sources_filtered:
            # do not colorize if a key is really mixed-source
            colorized_key = path[-1]
        else:
            colorized_key = _color_for_source(path[-1], sources[0])
        replace_key_at_path(
            metadata,
            path,
            colorized_key,
        )
        return colorized_key


def _sort_dict_colorblind(old_dict):
    if version_info < (3, 7):
        new_dict = OrderedDict()
    else:
        new_dict = {}

    for key in sorted(old_dict.keys(), key=lambda k: ansi_clean(k)):
        if isinstance(old_dict[key], dict):
            new_dict[key] = _sort_dict_colorblind(old_dict[key])
        else:
            new_dict[key] = old_dict[key]

    return new_dict


def bw_metadata(repo, args):
    target_nodes = get_target_nodes(repo, args['targets'])
    key_paths = sorted([
        tuple(path.strip().split("/")) for path in args['keys'] if path
    ]) or [tuple()]
    if len(target_nodes) > 1:
        if key_paths == [tuple()]:
            io.stdout(_("{x} at least one key is required when viewing multiple nodes").format(x=red("!!!")))
            exit(1)
        if args['blame']:
            io.stdout(_("{x} blame information can only be shown for a single node").format(x=red("!!!")))
            exit(1)

        table = [[bold(_("node"))] + [bold("/".join(path)) for path in key_paths], ROW_SEPARATOR]
        for node in sorted(target_nodes):
            values = []
            for key_path in key_paths:
                value = node.metadata.get(key_path, default=red(_("<missing>")))
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
        node = target_nodes.pop()
        if args['blame']:
            table = [[bold(_("path")), bold(_("source"))], ROW_SEPARATOR]
            for key_path in key_paths:
                # ensure all paths have been generated and will be present in .blame
                node.metadata.get(key_path)
            for path, blamed in sorted(node.metadata.blame.items()):
                joined_path = "/".join(path)
                for key_path in key_paths:
                    if list_starts_with(path, key_path):
                        table.append([joined_path, ", ".join(blamed)])
                        break
            page_lines(render_table(table))
        else:
            metadata = {}
            for key_path in key_paths:
                set_key_at_path(metadata, key_path, node.metadata.get(key_path))

            blame = list(node.metadata.blame.items())
            # sort descending by key path length since we will be replacing
            # the keys and can't access paths beneath replaced keys anymore
            blame.sort(key=lambda e: len(e[0]), reverse=True)

            for path, blamed in blame:
                # remove all paths we did not ask to see
                for filtered_path in key_paths:
                    if (
                        list_starts_with(path, filtered_path) or
                        list_starts_with(filtered_path, path)
                    ):
                        break
                else:
                    with suppress(KeyError):
                        delete_key_at_path(metadata, path)
                    continue

                colorized_key = _colorize_path(
                    metadata,
                    path,
                    blamed,
                    args['hide_defaults'],
                    args['hide_reactors'],
                    args['hide_groups'],
                    args['hide_node'],
                )
                for key_path in key_paths:
                    if colorized_key and list(path) == key_path[:len(path)]:
                        # we just replaced a key in the filtered path
                        key_path[len(path) - 1] = colorized_key

            # now we need to recreate the dict, sorting the keys as if
            # they were not colored (otherwise we'd end up sorted by
            # color)
            metadata_sorted = _sort_dict_colorblind(metadata)

            page_lines([
                force_text(line).replace("\\u001b", "\033")
                for line in metadata_to_json(
                    metadata_sorted,
                    sort_keys=False,
                ).splitlines()
            ])
