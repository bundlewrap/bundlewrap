from os.path import isdir, join

from blockwart.utils import mark_for_translation as _

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
