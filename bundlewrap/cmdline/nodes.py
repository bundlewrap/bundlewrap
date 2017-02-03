# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from ..utils import names
from ..utils.cmdline import get_group, get_target_nodes
from ..utils.table import ROW_SEPARATOR, render_table
from ..utils.text import bold, mark_for_translation as _
from ..utils.ui import io, page_lines
from ..group import GROUP_ATTR_DEFAULTS


def bw_nodes(repo, args):
    if args['filter_group'] is not None:
        nodes = get_group(repo, args['filter_group']).nodes
    elif args['target'] is not None:
        nodes = get_target_nodes(repo, args['target'], adhoc_nodes=args['adhoc_nodes'])
    else:
        nodes = repo.nodes

    rows = [[
        bold(_("node")),
        bold(_("attribute")),
        bold(_("value")),
    ], ROW_SEPARATOR]

    for node in nodes:
        if args['show_attrs']:
            first_attr = True
            for attr in sorted(list(GROUP_ATTR_DEFAULTS) + ['hostname']):
                rows.append([
                    node.name if first_attr else "",
                    attr,
                    str(getattr(node, attr)),
                ])
                first_attr = False

            if args['inline']:
                rows.append([
                    node.name if first_attr else "",
                    "group",
                    ", ".join(sorted([group.name for group in node.groups])),
                ])
                first_attr = False
            else:
                rows.append([
                    "",
                    "",
                    "",
                ])
                first_group = True
                for group in sorted(node.groups):
                    rows.append([
                        node.name if first_attr else "",
                        "group" if first_group else "",
                        group.name,
                    ])
                    first_group = False
                    first_attr = False
                rows.append([
                    "",
                    "",
                    "",
                ])

            if args['inline']:
                rows.append([
                    node.name if first_attr else "",
                    "bundle",
                    ", ".join(sorted([bundle.name for bundle in node.bundles])),
                ])
                first_attr = False
            else:
                first_bundle = True
                for bundle in sorted(node.bundles):
                    rows.append([
                        node.name if first_attr else "",
                        "bundle" if first_bundle else "",
                        bundle.name,
                    ])
                    first_bundle = False
                    first_attr = False
            rows.append(ROW_SEPARATOR)
            continue
        line = ""
        if args['show_hostnames']:
            line += node.hostname
        else:
            line += node.name
        if args['show_bundles']:
            line += ": " + ", ".join(sorted(names(node.bundles)))
        elif args['show_groups']:
            line += ": " + ", ".join(sorted(names(node.groups)))
        elif args['show_os']:
            line += ": " + node.os
        io.stdout(line)

    if len(rows) > 2:
        page_lines(render_table(
            rows[:-1],  # remove trailing ROW_SEPARATOR
        ))
