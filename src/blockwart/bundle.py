from os.path import join

from .exceptions import RepositoryError
from .utils import cached_property, get_all_attrs_from_file, validate_name
from .utils import mark_for_translation as _

FILENAME_BUNDLE = "bundle.py"


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

        self.bundle_dir = join(self.repo.bundles_dir, self.name)
        self.bundle_file = join(self.bundle_dir, FILENAME_BUNDLE)

    @cached_property
    def items(self):
        bundle_attrs = get_all_attrs_from_file(self.bundle_file)
        for item_class in self.repo.item_classes:
            if item_class.BUNDLE_ATTRIBUTE_NAME not in bundle_attrs:
                continue
            for name, attrs in bundle_attrs.get(
                    item_class.BUNDLE_ATTRIBUTE_NAME,
                    {},
            ).iteritems():
                yield item_class(self, name, attrs)
