# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from ..node import prepare_dependencies
from ..utils import graph_for_items


def bw_plot_node(repo, args):
    node = repo.get_node(args.node)
    for line in graph_for_items(
        node.name,
        prepare_dependencies(node.items),
        cluster=args.cluster,
        concurrency=args.depends_concurrency,
        static=args.depends_static,
        regular=args.depends_regular,
        reverse=args.depends_reverse,
        auto=args.depends_auto,
    ):
        yield line
