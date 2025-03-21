from collections import defaultdict
from collections.abc import Collection
from os import environ, makedirs
from os.path import dirname, exists, join
from sys import exit

from ..deps import prepare_dependencies
from ..exceptions import FaultUnavailable
from ..items import BUILTIN_ITEM_ATTRIBUTES
from ..utils.cmdline import get_item, get_node
from ..utils.dicts import statedict_to_json
from ..utils.table import ROW_SEPARATOR, render_table
from ..utils.text import bold, green, mark_for_translation as _, red, yellow
from ..utils.ui import io, page_lines


def write_preview(file_item, base_path):
    """
    Writes the content of the given file item to the given path.
    """
    # this might raise an exception, try it before creating anything
    content = file_item.content
    file_path = join(base_path, file_item.name.lstrip("/"))
    dir_path = dirname(file_path)
    if not exists(dir_path):
        makedirs(dir_path)
    with open(file_path, 'wb') as f:
        f.write(content)


def bw_items(repo, args):
    node = get_node(repo, args['node'])
    if args['preview'] and not args['item']:
        io.stderr(_("{x} no ITEM given for preview").format(x=red("!!!")))
        exit(1)
    elif args['file_preview_path']:
        if args['item']:
            io.stderr(_("{x} use --file-preview to preview single files").format(x=red("!!!")))
            exit(1)
        if exists(args['file_preview_path']):
            io.stderr(_(
                "not writing to existing path: {path}"
            ).format(path=args['file_preview_path']))
            exit(1)
        for item in sorted(node.items):
            if not item.id.startswith("file:"):
                continue
            if item.attributes['content_type'] == 'any':
                io.stderr(_(
                    "{x} skipped {filename} (content_type 'any')"
                ).format(x=yellow("»"), filename=bold(item.name)))
                continue
            if item.attributes['content_type'] == 'binary':
                io.stderr(_(
                    "{x} skipped {filename} (content_type 'binary')"
                ).format(x=yellow("»"), filename=bold(item.name)))
                continue
            if item.attributes['content_type'] == 'download':
                io.stderr(_(
                    "{x} skipped {filename} (content_type 'download')"
                ).format(x=yellow("»"), filename=bold(item.name)))
                continue
            if item.attributes['delete']:
                io.stderr(_(
                    "{x} skipped {filename} ('delete' attribute set)"
                ).format(x=yellow("»"), filename=bold(item.name)))
                continue
            try:
                write_preview(item, args['file_preview_path'])
            except FaultUnavailable:
                io.stderr(_(
                    "{x} skipped {path} (Fault unavailable)"
                ).format(x=yellow("»"), path=bold(item.name)))
            else:
                io.stdout(_(
                    "{x} wrote {path}"
                ).format(
                    x=green("✓"),
                    path=bold(join(
                        args['file_preview_path'],
                        item.name.lstrip("/"),
                    )),
                ))
    elif args['item']:
        item = get_item(node, args['item'])
        if args['preview']:
            try:
                io.stdout(
                    item.preview(),
                    append_newline=False,
                )
            except NotImplementedError:
                io.stderr(_(
                    "{x} cannot preview {item} on {node} (doesn't support previews)"
                ).format(x=red("!!!"), item=item.id, node=node.name))
                exit(1)
            except ValueError:
                io.stderr(_(
                    "{x} cannot preview {item} on {node} (not available for this item config)"
                ).format(x=red("!!!"), item=item.id, node=node.name))
                exit(1)
            except FaultUnavailable:
                io.stderr(_(
                    "{x} cannot preview {item} on {node} (Fault unavailable)"
                ).format(x=red("!!!"), item=item.id, node=node.name))
                exit(1)
        else:
            if args['show_attrs']:
                prepare_dependencies(node)
                table = [[bold(_("attribute")), bold(_("value"))]]
                for attribute in BUILTIN_ITEM_ATTRIBUTES:
                    if args['attr'] and attribute != args['attr']:
                        continue
                    table.append(ROW_SEPARATOR)
                    value = getattr(item, attribute)
                    if isinstance(value, str):
                        table.append([attribute, value])
                    elif isinstance(value, Collection):
                        value = sorted(value) or [""]
                        table.append([attribute, value.pop(0)])
                        for element in value:
                            table.append([
                                attribute if environ.get('BW_TABLE_STYLE') == "grep" else "",
                                element,
                            ])
                    else:
                        table.append([attribute, repr(value)])
                page_lines(render_table(table))
            else:
                if item.ITEM_TYPE_NAME == "action":
                    statedict = item.attributes
                elif args['show_sdict']:
                    statedict = item.sdict()
                else:
                    statedict = item.cdict()
                if statedict is None:
                    io.stdout("REMOVE")
                else:
                    if args['attr']:
                        io.stdout(repr(statedict[args['attr']]))
                    else:
                        io.stdout(statedict_to_json(statedict, pretty=True))
    else:
        items_per_bundle = defaultdict(list)
        for item in sorted(node.items):
            if args['blame']:
                if args['show_repr']:
                    items_per_bundle[item.bundle.name].append(repr(item))
                else:
                    items_per_bundle[item.bundle.name].append(item.id)
            elif args['show_repr']:
                io.stdout(repr(item))
            else:
                io.stdout(item.id)

        if args['blame']:
            blame_table = [
                [_("bundle name"), _("items")],
            ]
            for bundle_name, items in sorted(items_per_bundle.items()):
                first_line = True
                blame_table.append(ROW_SEPARATOR)
                for item in items:
                    if first_line:
                        blame_table.append([bundle_name, item])
                    else:
                        blame_table.append(["", item])
                    first_line = False
            page_lines(render_table(blame_table))
