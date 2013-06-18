from os.path import isdir, join

from .exceptions import NoSuchGroup, NoSuchNode, RepositoryError
from .group import Group
from .node import Node
from .utils import cached_property, getattr_from_file, \
    mark_for_translation as _

FILENAME_GROUPS = "groups.py"
FILENAME_NODES = "nodes.py"

INITIAL_CONTENT = {
    FILENAME_GROUPS: _("""
groups = {
    #'group1': {
    #    'subgroups': (
    #        'group2',
    #    ),
    #    'bundles': (
    #        'bundle1',
    #    ),
    #    'nodes': (
    #        'node1',
    #    ),
    #},
    'all': {
    },
}

# node names matching these regexes
# will be added to the corresponding groups
group_patterns {
    r".*": "all",
}
    """),

    FILENAME_NODES: _("""
nodes = {
    'node1': {
        'hostname': "localhost",
    },
}
    """),
}


class Repository(object):
    def __init__(self, repo_path):
        self.path = repo_path
        if not isdir(self.path):
            raise RepositoryError(
                _("'{}' is not a directory").format(self.path)
            )

    def create(self):
        """
        Sets up initial content for a repository.
        """
        for filename, content in INITIAL_CONTENT.iteritems():
            with open(join(self.path, filename), 'w') as f:
                f.write(content.strip() + "\n")

    def get_group(self, group_name):
        try:
            return self.group_dict[group_name]
        except KeyError:
            raise NoSuchGroup(group_name)

    def get_node(self, node_name):
        try:
            return self.node_dict[node_name]
        except KeyError:
            raise NoSuchNode(node_name)

    @cached_property
    def group_dict(self):
        try:
            flat_group_dict = getattr_from_file(
                self.groups_file,
                'groups',
            )
        except KeyError:
            raise RepositoryError(
                _("{} must define a 'nodes' variable").format(
                    self.groups_file,
                )
            )
        groups = {}
        for groupname, infodict in flat_group_dict.iteritems():
            groups[groupname] = Group(self, groupname, infodict)
        return groups

    @property
    def groups(self):
        result = list(self.group_dict.values())
        result.sort()
        return result

    @cached_property
    def groups_file(self):
        return join(self.path, FILENAME_GROUPS)

    def groups_for_node(self, node):
        for group in self.groups:
            if node in group.nodes:
                yield group

    @cached_property
    def node_dict(self):
        try:
            flat_node_dict = getattr_from_file(
                self.nodes_file,
                'nodes',
            )
        except KeyError:
            raise RepositoryError(
                _("{} must define a 'nodes' variable").format(
                    self.nodes_file,
                )
            )
        nodes = {}
        for nodename, infodict in flat_node_dict.iteritems():
            nodes[nodename] = Node(self, nodename, infodict)
        return nodes

    @property
    def nodes(self):
        result = list(self.node_dict.values())
        result.sort()
        return result

    @cached_property
    def nodes_file(self):
        return join(self.path, FILENAME_NODES)
