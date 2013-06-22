from .exceptions import RepositoryError
from .utils import mark_for_translation as _, validate_name


class Bundle(object):
    """
    A collection of config items, bound to a node.
    """
    def __init__(self, node, name):
        self.name = name
        self.node = node
        self.repo = node.repo

        if not validate_name(name):
            raise RepositoryError(_("invalid bundle name: {}").format(name))

        if not name in self.repo.bundle_names:
            raise RepositoryError(_("bundle not found: {}").format(name))
