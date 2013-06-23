"""
Note that modules in this package have to use absolute imports because
Repository.config_item_classes loads them as files.
"""
CONFIG_ITEM_CLASSES = {}
CONFIG_ITEM_CLASSES_LOADED = False


class ConfigItemStatus(object):
    """
    Holds information on a particular ConfigItem such as whether it needs
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
        return "<ConfigItemStatus correct:{}>".format(self.correct)


class ConfigItem(object):
    """
    A single piece of literal config (e.g. a file, a package, a service).
    """
    BUNDLE_ATTR_NAME = None
    ITEM_TYPE_NAME = None

    depends_static = []

    def __init__(self, bundle, name, attrs):
        self.attrs = attrs
        self.bundle = bundle
        self.name = name
