"""
Note that modules in this package have to use absolute imports because
Repository.item_classes loads them as files.
"""
from copy import copy
from os.path import join

from blockwart.exceptions import BundleError
from blockwart.utils.text import mark_for_translation as _
from blockwart.utils.ui import ask_interactively

BUILTIN_ITEM_ATTRIBUTES = {
    "depends": [],
}
ITEM_CLASSES = {}
ITEM_CLASSES_LOADED = False


class ItemStatus(object):
    """
    Holds information on a particular Item such as whether it needs
    fixing, a description of what's wrong etc.
    """

    def __init__(
        self,
        correct=True,
        description="No description available.",
        fixable=True,
        info=None,
    ):
        self.aborted = False
        self.correct = correct
        self.description = description
        self.fixable = fixable
        self.info = {} if info is None else info

    def __repr__(self):
        return "<ItemStatus correct:{}>".format(self.correct)


class Item(object):
    """
    A single piece of configuration (e.g. a file, a package, a service).
    """
    BUNDLE_ATTRIBUTE_NAME = None
    DEPENDS_STATIC = []
    ITEM_ATTRIBUTES = {}
    ITEM_TYPE_NAME = None

    def __init__(self, bundle, name, attributes, skip_validation=False):
        self.attributes = {}
        self.bundle = bundle
        self.item_dir = join(bundle.bundle_dir, self.BUNDLE_ATTRIBUTE_NAME)
        self.name = name
        self.node = bundle.node

        if not skip_validation:
            self._validate_attribute_names(attributes)
            self.validate_attributes(attributes)

        for attribute_name, attribute_default in \
                self.ITEM_ATTRIBUTES.iteritems():
            if attribute_name in BUILTIN_ITEM_ATTRIBUTES:
                continue
            self.attributes[attribute_name] = attributes.get(
                attribute_name,
                attribute_default,
            )

        for attribute_name, attribute_default in \
                BUILTIN_ITEM_ATTRIBUTES.iteritems():
            setattr(self, attribute_name, attributes.get(
                attribute_name,
                copy(attribute_default),
            ))

    def __repr__(self):
        return "<Item {}>".format(self.id)

    def _validate_attribute_names(self, attributes):
        invalid_attributes = set(attributes.keys()).difference(
            set(self.ITEM_ATTRIBUTES.keys()).union(
                set(BUILTIN_ITEM_ATTRIBUTES.keys())
            ),
        )
        if invalid_attributes:
            raise BundleError(
                _("invalid attribute(s) for '{}' in bundle '{}': {}").format(
                    self.id,
                    self.bundle.name,
                    ", ".join(invalid_attributes),
                )
            )

    @property
    def id(self):
        return "{}:{}".format(self.ITEM_TYPE_NAME, self.name)

    def apply(self, interactive=False, interactive_default=True,
              recheck=False):
        status_before = self.get_status()
        status_after = None
        if status_before.correct or not status_before.fixable:
            status_after = copy(status_before)
        else:
            if not interactive:
                self.fix(status_before)
            else:
                if ask_interactively(self.ask(status_before),
                                     interactive_default):
                    self.fix(status_before)
                else:
                    status_after = copy(status_before)
                    status_after.aborted = True
            if recheck:
                status_after = self.get_status()
        return (status_before, status_after)

    def ask(self, status):
        """
        Returns a string asking the user if this item should be
        implemented.

        MUST be overridden by subclasses.
        """
        raise NotImplementedError()

    def fix(self, status):
        """
        This is supposed to actually implement stuff on the target node.

        MUST be overridden by subclasses.
        """
        raise NotImplementedError()

    def get_status(self):
        """
        Returns an ItemStatus instance describing the current status of
        the item on the actual node. Must not be cached.

        MUST be overridden by subclasses.
        """
        raise NotImplementedError()

    def validate_attributes(self, attributes):
        """
        Raises BundleError if something is amiss with the user-specified
        attributes.

        SHOULD be overridden by subclasses.
        """
        pass
