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
    REPR = 'repr'


def bw_items(repo, args):
    node = get_node(repo, args['node'])
    if args['file_preview_path']:  # -w / --write-file-previews
        render_file_previews(node, args['file_preview_path'], args)

    elif args['item']:  # [ITEM] specified
        item = get_item(node, args['item'])
        if args['preview']:  # -f / --preview
            representation = ItemRepresentation.PREVIEW
        elif args['show_attrs']:  # -a / --attrs
            representation = ItemRepresentation.ATTRS
        elif args['show_sdict']:  # --state
            representation = ItemRepresentation.SDICT
        elif args['show_repr']:  # --repr
            representation = ItemRepresentation.REPR
        else:
            representation = ItemRepresentation.CDICT

        show_single_item(node, item, representation, args)

    else:
        list_all_items(node, args)


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


def render_file_previews(node, file_preview_path, args):
    if args['item']:
        io.stderr(_("{x} use --preview to preview single files").format(x=red("!!!")))
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


def show_single_item(node, item, representation, args):
    if representation == ItemRepresentation.PREVIEW:
        show_single_item_preview(node, item)
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

    elif representation == ItemRepresentation.REPR:
        data = [repr(item)]
        format_data(data, args['format'], table_headers=[_('item')])
        return

    # print attributes key-value
    format_data(data, args['format'], table_headers=[_('attribute'), _('value')])


def show_single_item_preview(node, item):
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


def list_all_items(node, args):
    show_repr = args['show_repr']
    if args['blame']:
        # items per bundles
        data = defaultdict(list)
        table_headers = [_("bundle name"), _("items")]
        for item in sorted(node.items):
            data[item.bundle.name].append(repr(item) if show_repr else item.id)

    else:
        # items list
        data = []
        table_headers = [_('items')]
        for item in sorted(node.items):
            data.append(repr(item) if show_repr else item.id)

    format_data(data, args['format'], table_headers=table_headers)


def format_data(data, fmt, table_headers=None):
    if fmt == 'json':
        io.stdout(statedict_to_json(data, pretty=True))

    elif fmt == 'table':
        format_data_table(data, table_headers)


def format_data_table(data, table_headers):
    table = [
        [
            bold(header)
            for header in table_headers
        ]
    ]

    if isinstance(data, (list, set)):
        table.append(ROW_SEPARATOR)
        for v in sorted(data):  # iterate a list
            if isinstance(v, (list, set)):
                for vv in sorted(v):  # iterate inner list of lists
                    table.append([str(vv)])
            else:
                # value in list
                table.append([str(v)])

    elif isinstance(data, dict):
        for k, v in sorted(data.items()):  # iterate items in dict
            table.append(ROW_SEPARATOR)
            if isinstance(v, (list, set)):
                first_line = True
                if len(v) == 0:
                    table.append([str(k), "[]"])
                    continue

                for vv in sorted(v):  # iterate list-value
                    if first_line:
                        table.append([str(k), str(vv)])
                        first_line = False
                    else:
                        table.append(["", str(vv)])
            else:
                table.append([str(k), str(v)])

    page_lines(render_table(table))
