from .exceptions import RepositoryError
from .utils import cached_property, getattr_from_file
from .utils import mark_for_translation as _


def _build_error_chain(loop_node, last_node, nodes_in_between):
    """
    Used to illustrate subgroup loop paths in error messages.

    loop_node:          name of node that loops back to itself
    last_node:          name of last node pointing back to loop_node,
                        causing the loop
    nodes_in_between:   names of nodes traversed during loop detection,
                        does include loop_node if not a direct loop,
                        but not last_node
    """
    error_chain = []
    for visited in nodes_in_between:
        if (loop_node in error_chain) != (loop_node == visited):
            error_chain.append(visited)
    error_chain.append(last_node)
    error_chain.append(loop_node)
    return error_chain


class Group(object):
    """
    A group of nodes.
    """
    def __init__(self, repo, group_name, infodict):
        self.name = group_name
        self.repo = repo
        self.immediate_subgroup_names = infodict.get('subgroups', [])

    def __eq__(self, other):
        return self.name == other.name

    def __repr__(self):
        return "<Group: {}>".format(self.name)

    def __str__(self):
        return self.name

    @cached_property
    def nodes(self):
        """
        Iterator for all nodes in this group.
        """
        profile_patterns = getattr_from_file(
            self.repo.groups_file,
            'profile_patterns',
            default={},
        )
        # TODO

    def _check_subgroup_names(self, visited_names):
        """
        Recursively finds subgroups and checks for loops.
        """
        for name in self.immediate_subgroup_names:
            if name not in visited_names:
                group = self.repo.get_group(name)
                for group_name in group._check_subgroup_names(
                    visited_names + [self.name],
                ):
                    yield group_name
            else:
                error_chain = _build_error_chain(
                    name,
                    self.name,
                    visited_names,
                )
                raise RepositoryError(
                    _("{} can't be a subgroup of itself "
                      "({})").format(
                          name,
                          " -> ".join(error_chain),
                      )
                )
        if self.name not in visited_names:
            yield self.name

    @cached_property
    def subgroups(self):
        """
        Iterator over all subgroups as group objects.
        """
        for group_name in self._check_subgroup_names([self.name]):
            yield self.repo.get_group(group_name)
