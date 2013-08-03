from ..exceptions import NoSuchNode, NoSuchGroup, UsageException
from ..utils.text import mark_for_translation as _


def get_target_nodes(repo, target_string):
    """
    Returns a list of nodes. The input is a string like "node1,node2,group3".
    """
    targets = []
    for name in target_string.split(","):
        name = name.strip()
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
