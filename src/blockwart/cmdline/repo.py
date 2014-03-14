# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from code import interact
from copy import copy
from sys import exit

from .. import VERSION_STRING
from ..concurrency import WorkerPool
from ..exceptions import WorkerException
from ..node import prepare_dependencies
from ..repo import Repository
from ..utils.cmdline import get_target_nodes
from ..utils.text import mark_for_translation as _, red


DEBUG_BANNER = _("Blockwart {version} interactive repository inspector\n"
                 "> You can access the current repository as 'repo'."
                 "").format(version=VERSION_STRING)

DEBUG_BANNER_NODE = DEBUG_BANNER + "\n" + \
    _("> You can access the selected node as 'node'.")


def bw_repo_bundle_create(repo, args):
    repo.create_bundle(args.bundle)


def bw_repo_create(path, args):
    Repository.create(path)


def bw_repo_debug(repo, args):
    repo = Repository(repo.path)
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
        yield "\"bundle:{}\"".format(bundle.name)
        for item in bundle.items:
            yield "\"{}\"".format(item.id)
        yield "}"

    items = prepare_dependencies(node.items)

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


def bw_repo_test(repo, args):
    if args.target:
        target_nodes = get_target_nodes(repo, args.target)
    else:
        target_nodes = copy(list(repo.nodes))
    with WorkerPool(workers=args.node_workers) as worker_pool:
        while worker_pool.keep_running():
            try:
                msg = worker_pool.get_event()
            except WorkerException as e:
                msg = "{} {}\n".format(
                    red("✘"),
                    e.task_id,
                )
                yield msg
                yield e.traceback
                exit(1)
                break  # for testing, when exit() is patched
            if msg['msg'] == 'REQUEST_WORK':
                if target_nodes:
                    node = target_nodes.pop()
                    worker_pool.start_task(
                        msg['wid'],
                        node.test,
                        task_id=node.name,
                        kwargs={
                            'workers': args.item_workers,
                        },
                    )
                else:
                    worker_pool.quit(msg['wid'])
