# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from code import interact

from .. import VERSION_STRING
from ..node import flatten_dependencies, inject_concurrency_blockers, inject_dummy_items
from ..repo import Repository
from ..utils.text import mark_for_translation as _


DEBUG_BANNER = _("blockwart {} interactive repository inspector\n"
                 "> You can access the current repository as 'repo'."
                 "").format(VERSION_STRING)

DEBUG_BANNER_NODE = DEBUG_BANNER + "\n" + \
    _("> You can access the selected node as 'node'.")


def bw_repo_create(repo, args):
    repo.create()


def bw_repo_debug(repo, args):
    repo = Repository(repo.path, skip_validation=False)
    if args.node is None:
        interact(DEBUG_BANNER, local={'repo': repo})
    else:
        node = repo.get_node(args.node)
        interact(DEBUG_BANNER_NODE, local={'node': node, 'repo': repo})


def bw_repo_plot(repo, args):
    node = repo.get_node(args.node)

    yield "digraph blockwart"
    yield "{"

    # Print subgraphs *below* each other
    yield "rankdir = LR"

    # Global attributes
    yield ("graph [color=\"#303030\"; "
                  "fontname=Helvetica; "
                  "penwidth=2; "
                  "shape=box; "
                  "style=\"rounded,dashed\"]")
    yield ("node [color=\"#303030\"; "
                 "fillcolor=\"#303030\"; "
                 "fontcolor=white; "
                 "fontname=Helvetica; "
                 "shape=box; "
                 "style=\"rounded,filled\"]")
    yield "edge [arrowhead=vee]"

    # Define which items belong to which bundle
    bundle_number = 0
    for bundle in node.bundles:
        yield "subgraph cluster_{}".format(bundle_number)
        bundle_number += 1
        yield "{"
        yield "label = \"{}\"".format(bundle.name)
        for item in bundle.items:
            yield "\"{}\"".format(item.id)
        yield "}"

    items = list(node.items)

    for item in items:
        # merge static and user-defined deps
        item._deps = list(item.DEPENDS_STATIC)
        item._deps += item.depends

    items = inject_dummy_items(items)
    items = flatten_dependencies(items)
    items = inject_concurrency_blockers(items)

    # Define dependencies between items
    for item in items:
        if args.depends_static:
            for dep in item.DEPENDS_STATIC:
                yield "\"{}\" -> \"{}\" [color=\"#3991CC\",penwidth=2]".format(item.id, dep)

        if args.depends_regular:
            for dep in item.depends:
                yield "\"{}\" -> \"{}\" [color=\"#C24948\",penwidth=2]".format(item.id, dep)

        if args.depends_auto:
            for dep in item._deps:
                if dep not in item.DEPENDS_STATIC and dep not in item.depends:
                    yield "\"{}\" -> \"{}\" [color=\"#6BB753\",penwidth=2]".format(item.id, dep)

    # Global graph title
    yield "fontsize = 28"
    yield "label = \"{}\"".format(node.name)
    yield "labelloc = \"t\""
    yield "}"
