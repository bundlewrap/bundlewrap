from os import environ
from sys import exit

from ..utils import names
from ..utils.cmdline import get_target_nodes
from ..utils.table import ROW_SEPARATOR, render_table
from ..utils.text import bold, mark_for_translation as _, red
from ..utils.ui import io, page_lines
from ..group import GROUP_ATTR_DEFAULTS


NODE_ATTRS = sorted(list(GROUP_ATTR_DEFAULTS) + ['bundles', 'file_path', 'groups', 'hostname'])
NODE_ATTRS_LISTS = ('bundles', 'groups')


def _attribute_table(
    entities,
    entity_label,
    selected_attrs,
    available_attrs,
    available_attrs_lists,
    inline,
):
    rows = [[entity_label], ROW_SEPARATOR]
    selected_attrs = [attr.strip() for attr in selected_attrs]

    if selected_attrs == ['all']:
        selected_attrs = available_attrs
    elif 'all' in selected_attrs:
        io.stderr(_(
            "{x} invalid attribute list requested ('all' and extraneous): {attr}"
        ).format(x=red("!!!"), attr=", ".join(sorted(selected_attrs))))
        exit(1)

    for attr in selected_attrs:
        if attr not in available_attrs:
            io.stderr(_("{x} unknown attribute: {attr}").format(x=red("!!!"), attr=attr))
            exit(1)
        rows[0].append(bold(attr))

    has_list_attrs = False
    for entity in sorted(entities):
        attr_values = [[entity.name]]
        for attr in selected_attrs:
            if attr in available_attrs_lists:
                if inline:
                    attr_values.append([",".join(sorted(names(getattr(entity, attr))))])
                else:
                    has_list_attrs = True
                    attr_values.append(sorted(names(getattr(entity, attr))))
            else:
                attr_values.append([str(getattr(entity, attr))])
        number_of_lines = max([len(value) for value in attr_values])
        if environ.get("BW_TABLE_STYLE") == 'grep':
            # repeat entity name for each line
            attr_values[0] = attr_values[0] * number_of_lines
        for line in range(number_of_lines):
            row = []
            for attr_index in range(len(selected_attrs) + 1):
                try:
                    row.append(attr_values[attr_index][line])
                except IndexError:
                    row.append("")
            rows.append(row)
        if has_list_attrs:
            rows.append(ROW_SEPARATOR)
    if environ.get("BW_TABLE_STYLE") == 'grep':
        rows = rows[2:]
    page_lines(render_table(
        rows[:-1] if has_list_attrs else rows,  # remove trailing ROW_SEPARATOR
    ))


def bw_nodes(repo, args):
    if args['targets']:
        nodes = get_target_nodes(repo, args['targets'])
    else:
        nodes = repo.nodes
    if not args['attrs']:
        for node in sorted(nodes):
            io.stdout(node.name)
    else:
        _attribute_table(
            nodes,
            bold(_("node")),
            args['attrs'],
            NODE_ATTRS,
            NODE_ATTRS_LISTS,
            args['inline'],
        )
