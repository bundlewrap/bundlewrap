from .exceptions import RepositoryError
from .utils import cached_property, getattr_from_file


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
                error_chain = []
                for visited in visited_names:
                    if (name in error_chain) != (name == visited):
                        error_chain.append(visited)
                error_chain.append(self.name)
                error_chain.append(name)

                raise RepositoryError(
                    "{} can't be a subgroup of itself "
                    "({})".format(
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
