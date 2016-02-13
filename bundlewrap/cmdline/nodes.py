# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from ..utils import names


def bw_nodes(repo, args):
    if args['filter_group'] is not None:
        nodes = repo.get_group(args['filter_group']).nodes
    else:
        nodes = repo.nodes
    for node in nodes:
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
