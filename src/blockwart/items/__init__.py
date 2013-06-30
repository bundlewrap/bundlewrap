"""
Note that modules in this package have to use absolute imports because
Repository.item_classes loads them as files.
"""
from blockwart.exceptions import BundleError
from blockwart.utils import mark_for_translation as _

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
        status_info=None,
    ):
        self.correct = correct
        self.description = description
        self.fixable = fixable
        self.status_info = {} if status_info is None else status_info

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
        self.name = name

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
                attribute_default,
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

    def validate_attributes(self, attributes):
        """
        Raises BundleError if something is amiss with the user-specified
        attributes.

        SHOULD be overridden by subclasses.
        """
        pass
