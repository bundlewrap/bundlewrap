from os.path import join

from .exceptions import NoSuchBundle, RepositoryError
from .utils import cached_property, get_all_attrs_from_file
from .utils.text import mark_for_translation as _
from .utils.text import validate_name


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
            raise NoSuchBundle(_("bundle not found: {}").format(name))

        self.bundle_dir = join(self.repo.bundles_dir, self.name)
        self.bundle_data_dir = join(self.repo.data_dir, self.name)
        self.bundle_file = join(self.bundle_dir, FILENAME_BUNDLE)

    def __getstate__(self):
        """
        Removes cached items prior to pickling because their classed are
        loaded dynamically and can't be pickled.
        """
        try:
            del self._cache['items']
        except:
            pass
        return self.__dict__

    @cached_property
    def items(self):
        bundle_attrs = get_all_attrs_from_file(
            self.bundle_file,
            base_env={
                'node': self.node,
                'repo': self.repo,
            },
        )
        for item_class in self.repo.item_classes:
            if item_class.BUNDLE_ATTRIBUTE_NAME not in bundle_attrs:
                continue
            for name, attrs in bundle_attrs.get(
                    item_class.BUNDLE_ATTRIBUTE_NAME,
                    {},
            ).items():
                yield item_class(self, name, attrs)
