import enum
from collections import defaultdict
from os import makedirs
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


class ItemRepresentation(enum.Enum):
    PREVIEW = 'preview'
    ATTRS = 'attrs'
    SDICT = 'sdict'
    CDICT = 'cdict'


def bw_items(repo, args):
    node = get_node(repo, args['node'])
    if args['file_preview_path']:  # -w / --write-file-previews
        bw_items_render_file_previews(repo, node, args['file_preview_path'], args)

    elif args['item']:  # [ITEM] specified
        item = get_item(node, args['item'])
        if args['preview']:  # -f / --preview
            representation = ItemRepresentation.PREVIEW
        elif args['show_attrs']:  # -a / --attrs
            representation = ItemRepresentation.ATTRS
        elif args['show_sdict']:  # --state
            representation = ItemRepresentation.SDICT
        else:
            representation = ItemRepresentation.CDICT

        bw_items_show_single_item(repo, node, item, representation, args)

    else:
        bw_items_list_all_items(repo, node, args)


def write_preview(file_item, base_path):
    """
    Writes the content of a single file item to the given path.
    """
    # this might raise an exception, try it before creating anything
    content = file_item.content
    file_path = join(base_path, file_item.name.lstrip("/"))
    dir_path = dirname(file_path)
    if not exists(dir_path):
        makedirs(dir_path)
    with open(file_path, 'wb') as f:
        f.write(content)


def bw_items_render_file_previews(repo, node, file_preview_path, args):
    if args['item']:
        io.stderr(_("{x} use --file-preview to preview single files").format(x=red("!!!")))
        exit(1)
    if exists(file_preview_path):
        io.stderr(_(
            "not writing to existing path: {path}"
        ).format(path=file_preview_path))
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
            write_preview(item, file_preview_path)
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
                    file_preview_path,
                    item.name.lstrip("/"),
                )),
            ))


def bw_items_show_single_item(repo, node, item, representation, args):
    if representation == ItemRepresentation.PREVIEW:
        bw_items_show_single_item_preview(repo, node, item, args)
        return

    data = {}
    if representation == ItemRepresentation.ATTRS:
        prepare_dependencies(node)
        for attribute in BUILTIN_ITEM_ATTRIBUTES:
            if args['attr'] and attribute != args['attr']:
                continue

            value = getattr(item, attribute)
            data[attribute] = value

    elif item.ITEM_TYPE_NAME == "action":
        # actions don't have a state and thus no sdict or cdict
        data = item.attributes

    elif representation == ItemRepresentation.SDICT:
        data = item.sdict()

    elif representation == ItemRepresentation.CDICT:
        data = item.cdict()

    # TODO add more formatting options here
    if args['attr']:
        io.stdout(repr(data[args['attr']]))
    else:
        io.stdout(statedict_to_json(data, pretty=True))


def bw_items_show_single_item_preview(repo, node, item, args):
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

def bw_items_list_all_items(repo, node, args):
    if args['blame']:
        data = defaultdict(list)
        for item in sorted(node.items):
            data[item.bundle.name].append(item.id)
    else:
        data = []
        for item in sorted(node.items):
            data.append(item.id)

    # TODO add more formatting options here, especially the blame-table and the flat items list are pretty important
    io.stdout(statedict_to_json(data, pretty=True))
