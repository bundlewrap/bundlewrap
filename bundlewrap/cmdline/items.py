import enum
from collections import defaultdict
from os import makedirs
from os.path import dirname, exists, join
from sys import exit

from ..deps import prepare_dependencies
from ..exceptions import FaultUnavailable
from ..items import BUILTIN_ITEM_ATTRIBUTES
from ..utils.cmdline import get_item, get_node
from ..utils.dicts import state_dict_to_json
from ..utils.table import ROW_SEPARATOR, render_table
from ..utils.text import bold, green, mark_for_translation as _, red, yellow
from ..utils.ui import io, page_lines


class ItemRepresentation(enum.Enum):
    PREVIEW = 'preview'
    ATTRS = 'attrs'
    ACTUAL_STATE = 'actual_state'
    EXPECTED_STATE = 'expected_state'
    REPR = 'repr'


def bw_items(repo, args):
    """
    Implementation for the `bw items` command
    """
    node = get_node(repo, args['node'])
    if args['file_preview_path']:  # -w / --write-file-previews
        render_file_previews(node, args['file_preview_path'], args)

    elif args['item']:  # [ITEM] specified
        item = get_item(node, args['item'])
        if args['preview']:  # -f / --preview
            representation = ItemRepresentation.PREVIEW
        elif args['show_attrs']:  # -a / --attrs
            representation = ItemRepresentation.ATTRS
        elif args['show_actual_state']:  # --state
            representation = ItemRepresentation.ACTUAL_STATE
        elif args['show_repr']:  # --repr
            representation = ItemRepresentation.REPR
        else:
            representation = ItemRepresentation.EXPECTED_STATE

        show_single_item(node, item, representation, args)

    else:
        list_all_items(node, args)


def render_file_previews(node, file_preview_path, args):
    """
    Implementation for `bw items --write-file-previews`: Writes all file-items into a local directory.
    """
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
            write_file_preview(item, file_preview_path)
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


def write_file_preview(file_item, base_path):
    """
    Writes the content of a single file item to the given path.
    """

    # this might raise an exception, try it before creating anything
    content = file_item.content

    # write content to named file
    file_path = join(base_path, file_item.name.lstrip("/"))
    dir_path = dirname(file_path)
    if not exists(dir_path):
        makedirs(dir_path)
    with open(file_path, 'wb') as f:
        f.write(content)


def show_single_item(node, item, representation, args):
    """
    Implementation for all variants of `bw items NODE ITEM`.
    """
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
        # actions don't have a state and thus no state-dict
        data = item.attributes

    elif representation == ItemRepresentation.ACTUAL_STATE:
        data = item.actual_state()

    elif representation == ItemRepresentation.EXPECTED_STATE:
        data = item.expected_state()

    elif representation == ItemRepresentation.REPR:
        data = [repr(item)]
        format_data(data, args, table_headers=[_('item')])
        return

    # print attributes key-value
    format_data(data, args, table_headers=[_('attribute'), _('value')])


def show_single_item_preview(node, item):
    """
    Implementation of `bw items NODE ITEM --preview`: Writes the content of single file to stdout.
    """
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
    """
    Implementation of `bw items NODE`: Lists all items on a node.
    """
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

    format_data(data, args, table_headers=table_headers)


def format_data(data, args, table_headers=None):
    """
    Formats a list or a dict (with scalar or list values) according to the requested format
    """
    if args['format_json']:
        io.stdout(state_dict_to_json(data, pretty=True))

    else:
        format_data_table(data, table_headers)


def format_data_table(data, table_headers):
    """
    Formats a list or a dict (with scalar or list values) as bw-style table
    """
    table = [
        [
            bold(header)
            for header in table_headers
        ]
    ]

    if isinstance(data, (list, set)):
        if isinstance(data, set):
            data = list(sorted(data))

        table.append(ROW_SEPARATOR)
        for v in data:
            table.append([v])

    elif isinstance(data, dict):
        for k, v in sorted(data.items()):  # iterate items in dict
            table.append(ROW_SEPARATOR)
            table.append([str(k), v])

    page_lines(render_table(table))
