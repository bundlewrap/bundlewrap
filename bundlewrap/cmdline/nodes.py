# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from ..utils import names
from ..utils.text import bold
from ..group import GROUP_ATTR_DEFAULTS


ATTR_MAX_LENGTH = max([len(attr) for attr in GROUP_ATTR_DEFAULTS])


def bw_nodes(repo, args):
    if args['filter_group'] is not None:
        nodes = repo.get_group(args['filter_group']).nodes
    else:
        nodes = repo.nodes
    max_node_name_length = 0 if not nodes else max([len(name) for name in names(nodes)])
    for node in nodes:
        if args['show_attrs']:
            for attr in sorted(list(GROUP_ATTR_DEFAULTS) + ['hostname']):
                yield "{}\t{}\t{}".format(
                    node.name.ljust(max_node_name_length),
                    bold(attr.ljust(ATTR_MAX_LENGTH)),
                    getattr(node, attr),
                )
            continue
        line = ""
        if args['show_hostnames']:
            line += node.hostname
        else:
            line += node.name
        if args['show_bundles']:
            line += ": " + ", ".join(names(node.bundles))
        elif args['show_groups']:
            line += ": " + ", ".join(names(node.groups))
        elif args['show_os']:
            line += ": " + node.os
        yield line
