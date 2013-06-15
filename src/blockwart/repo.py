from os.path import isdir, join

from .node import Node
from .utils import cached_property, getattr_from_file, \
    mark_for_translation as _

FILENAME_NODES = "nodes.py"

INITIAL_CONTENT = {
    "nodes.py": """
nodes = {
    #'node1': {
    #    'groups': (
    #        'group1',
    #        'group2',
    #    ),
    #},
}
    """,
}


class NoSuchNode(Exception):
    """
    Raised when a node of unknown name is requested.
    """
    pass


class RepositoryError(Exception):
    """
    Indicates that somethings is wrong with the current repository.
    """
    pass


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

    def get_node(self, node_name):
        try:
            return self.node_dict[node_name]
        except KeyError:
            raise NoSuchNode(node_name)

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
        return self.node_dict.values()

    @cached_property
    def nodes_file(self):
        return join(self.path, FILENAME_NODES)
