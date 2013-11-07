from code import interact

from .. import VERSION_STRING
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

    print("digraph blockwart")
    print("{")

    # Print subgraphs *below* each other
    print("rankdir = LR")

    # Global attributes
    print("graph [style=filled; fill=lightgrey]")
    print("node [style=filled; fillcolor=lightblue]")

    # Define which items belong to which bundle
    bundle_number = 0
    for bundle in node.bundles:
        print("subgraph cluster_{}".format(bundle_number))
        bundle_number += 1
        print("{")
        print("label = \"{}\"".format(bundle.name))
        for item in bundle.items:
            print("\"{}\"".format(item.id))
        print("}")

    # Define dependencies between items
    for item in node.items:
        deps = []
        if args.depends_static:
            deps += item.DEPENDS_STATIC
        if args.depends_regular:
            deps += item.depends
        for dep in deps:
            print("\"{}\" -> \"{}\"".format(item.id, dep))

    # Global graph title
    print("labelloc = \"t\"")
    print("fontsize = 36")
    print("label = \"{}\"".format(node.name))

    print("}")
