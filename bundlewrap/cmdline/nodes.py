# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from ..utils import names
from ..utils.cmdline import get_group, get_target_nodes
from ..utils.text import bold
from ..utils.ui import io
from ..group import GROUP_ATTR_DEFAULTS


ATTR_MAX_LENGTH = max([len(attr) for attr in GROUP_ATTR_DEFAULTS])


def bw_nodes(repo, args):
    if args['filter_group'] is not None:
        nodes = get_group(repo, args['filter_group']).nodes
    elif args['target'] is not None:
        nodes = get_target_nodes(repo, args['target'], adhoc_nodes=args['adhoc_nodes'])
    else:
        nodes = repo.nodes
    max_node_name_length = 0 if not nodes else max([len(name) for name in names(nodes)])
    for node in nodes:
        if args['show_attrs']:
            for attr in sorted(list(GROUP_ATTR_DEFAULTS) + ['hostname']):
                io.stdout("{}\t{}\t{}".format(
                    node.name.ljust(max_node_name_length),
                    bold(attr.ljust(ATTR_MAX_LENGTH)),
                    getattr(node, attr),
                ))
            for group in node.groups:
                io.stdout("{}\t{}\t{}".format(
                    node.name.ljust(max_node_name_length),
                    bold("group".ljust(ATTR_MAX_LENGTH)),
                    group.name,
                ))
            for bundle in node.bundles:
                io.stdout("{}\t{}\t{}".format(
                    node.name.ljust(max_node_name_length),
                    bold("bundle".ljust(ATTR_MAX_LENGTH)),
                    bundle.name,
                ))
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
