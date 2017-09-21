# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from os import environ
from sys import exit

from ..utils import names
from ..utils.cmdline import get_target_nodes
from ..utils.table import ROW_SEPARATOR, render_table
from ..utils.text import bold, mark_for_translation as _, red
from ..utils.ui import io, page_lines
from ..group import GROUP_ATTR_DEFAULTS


NODE_ATTRS = sorted(list(GROUP_ATTR_DEFAULTS) + ['bundles', 'groups', 'hostname'])
NODE_ATTRS_LISTS = ('bundles', 'groups')


def bw_nodes(repo, args):
    if args['target'] is not None:
        nodes = get_target_nodes(repo, args['target'], adhoc_nodes=args['adhoc_nodes'])
    else:
        nodes = repo.nodes
    if not args['attrs']:
        for node in nodes:
            io.stdout(node.name)
    else:
        rows = [[bold(_("node"))], ROW_SEPARATOR]
        selected_attrs = [attr.strip() for attr in args['attrs'].split(",")]
        if selected_attrs == ['all']:
            selected_attrs = NODE_ATTRS
        for attr in selected_attrs:
            if attr not in NODE_ATTRS:
                io.stderr(_("{x} unknown attribute: {attr}").format(x=red("!!!"), attr=attr))
                exit(1)
            rows[0].append(bold(attr))
        for node in nodes:
            attr_values = [[node.name]]
            for attr in selected_attrs:
                if attr in NODE_ATTRS_LISTS:
                    attr_values.append(list(names(getattr(node, attr))))
                else:
                    attr_values.append([str(getattr(node, attr))])
            number_of_lines = max([len(value) for value in attr_values])
            if environ.get("BW_TABLE_STYLE") == 'grep':
                # repeat node name for each line
                attr_values[0] = attr_values[0] * number_of_lines
            for line in range(number_of_lines):
                row = []
                for attr_index in range(len(selected_attrs) + 1):
                    try:
                        row.append(attr_values[attr_index][line])
                    except IndexError:
                        row.append("")
                rows.append(row)
            rows.append(ROW_SEPARATOR)
        if environ.get("BW_TABLE_STYLE") == 'grep':
            rows = rows[2:]
        page_lines(render_table(
            rows[:-1],  # remove trailing ROW_SEPARATOR
        ))
