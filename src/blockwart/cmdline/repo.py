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
from ..utils import graph_for_items
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
    for line in graph_for_items(
        node.name,
        prepare_dependencies(node.items),
        cluster=args.cluster,
        static=args.depends_static,
        regular=args.depends_regular,
        auto=args.depends_auto,
    ):
        yield line


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
