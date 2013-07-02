from ..exceptions import UsageException
from ..utils import mark_for_translation as _


def _get_target_list(repo, groups, nodes):
    target_nodes = []
    if groups:
        for group_name in groups.split(","):
            group_name = group_name.strip()
            group = repo.get_group(group_name)
            target_nodes += list(group.nodes)
    if nodes:
        for node_name in nodes.split(","):
            node_name = node_name.strip()
            node = repo.get_node(node_name)
            target_nodes.append(node)
    if not target_nodes:
        raise UsageException(_("specify at least one node or group"))
    target_nodes = list(set(target_nodes))
    target_nodes.sort()
    return tuple(target_nodes)


def bw_apply(repo, args):
    target_nodes = _get_target_list(repo, args.groups, args.nodes)
    for node in target_nodes:
        node.apply(interactive=args.interactive)
