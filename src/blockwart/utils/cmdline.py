from ..exceptions import NoSuchNode, NoSuchGroup, UsageException
from ..utils.text import mark_for_translation as _


def get_target_nodes(repo, target_string):
    """
    Returns a list of nodes. The input is a string like this:

    "node1,node2,group3,bundle:foo"

    Meaning: Targets are 'node1', 'node2', all nodes in 'group3',
    and all nodes with the bundle 'foo'.
    """
    targets = []
    for name in target_string.split(","):
        name = name.strip()
        if name.startswith("bundle:"):
            bundle_name = name.split(":", 1)[1]
            for node in repo.nodes:
                for bundle in node.bundles:
                    if bundle.name == bundle_name:
                        targets.append(node)
                        break
        else:
            try:
                targets.append(repo.get_node(name))
            except NoSuchNode:
                try:
                    targets += list(repo.get_group(name).nodes)
                except NoSuchGroup:
                    raise UsageException(_(
                        "unable to find group or node named '{}'"
                    ).format(name))
    targets = list(set(targets))
    targets.sort()
    return targets
