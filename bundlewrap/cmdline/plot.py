from ..deps import prepare_dependencies
from ..utils.plot import graph_for_items, plot_group, plot_node_groups
from ..utils.cmdline import get_group, get_node
from ..utils.ui import io


def bw_plot_group(repo, args):
    group = get_group(repo, args['group']) if args['group'] else None

    if args['show_nodes']:
        nodes = group.nodes if group else repo.nodes
    else:
        nodes = []

    if group:
        groups = [group]
        groups.extend(group.subgroups)
    else:
        groups = repo.groups

    for line in plot_group(groups, nodes, args['show_nodes']):
        io.stdout(line)


def bw_plot_node(repo, args):
    node = get_node(repo, args['node'])
    for line in graph_for_items(
        node.name,
        prepare_dependencies(node),
        cluster=args['cluster'],
        concurrency=args['depends_concurrency'],
        regular=args['depends_regular'],
        reverse=args['depends_reverse'],
        auto=args['depends_auto'],
    ):
        io.stdout(line)


def bw_plot_node_groups(repo, args):
    node = get_node(repo, args['node'])
    for line in plot_node_groups(node):
        io.stdout(line)
