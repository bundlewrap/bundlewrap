# -*- coding: utf-8 -*-
"""
Note that modules in this package have to use absolute imports because
Repository.item_classes loads them as files.
"""
from __future__ import unicode_literals
from copy import copy
from datetime import datetime
from os.path import join

from blockwart.exceptions import BundleError
from blockwart.utils import LOG
from blockwart.utils.text import mark_for_translation as _
from blockwart.utils.text import bold, wrap_question
from blockwart.utils.ui import ask_interactively

BUILTIN_ITEM_ATTRIBUTES = {
    "depends": [],
    "triggers": [],
    "unless": "",
}
ITEM_CLASSES = {}
ITEM_CLASSES_LOADED = False


def unpickle_item_class(class_name, bundle, name, attributes):
    for item_class in bundle.node.repo.item_classes:
        if item_class.__name__ == class_name:
            return item_class(bundle, name, attributes, skip_validation=True)
    raise RuntimeError(_("unable to unpickle {}").format(class_name))


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
    PARALLEL_APPLY = True
    REQUIRED_ATTRIBUTES = []

    def __init__(self, bundle, name, attributes, skip_validation=False):
        self.attributes = {}
        self.bundle = bundle
        self.item_dir = join(bundle.bundle_dir, self.BUNDLE_ATTRIBUTE_NAME)
        self.name = name
        self.node = bundle.node

        if not skip_validation:
            self.validate_name(bundle, name)
            self._validate_attribute_names(attributes)
            self._validate_required_attributes(attributes)
            self.validate_attributes(attributes)

        attributes = self.patch_attributes(attributes)

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

    def __str__(self):
        return self.id

    def __reduce__(self):
        attrs = copy(self.attributes)
        for attribute_name in BUILTIN_ITEM_ATTRIBUTES.keys():
            attrs[attribute_name] = getattr(self, attribute_name)
        return (
            unpickle_item_class,
            (
                self.__class__.__name__,
                self.bundle,
                self.name,
                attrs,
            ),
        )

    def __repr__(self):
        return "<Item {}>".format(self.id)

    def _check_bundle_collisions(self, items):
        for item in items:
            if item == self:
                continue
            if item.id == self.id:
                raise BundleError(_(
                    "duplicate definition of {} in bundles '{}' and '{}'"
                ).format(
                    item.id,
                    item.bundle.name,
                    self.bundle.name,
                ))

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

    def _validate_required_attributes(self, attributes):
        missing = []
        for attrname in self.REQUIRED_ATTRIBUTES:
            if attrname not in attributes:
                missing.append(attrname)
        if missing:
            raise BundleError(_("{} missing required attribute(s): {}").format(
                self.id,
                ", ".join(missing),
            ))

    @property
    def id(self):
        return "{}:{}".format(self.ITEM_TYPE_NAME, self.name)

    def apply(self, interactive=False, interactive_default=True):
        self.node.repo.hooks.item_apply_start(
            self.node.repo,
            self.node,
            self,
        )
        start_time = datetime.now()

        status_before = self.get_status()
        status_after = None

        if self.unless and not status_before.correct:
            unless_result = self.node.run(self.unless)
            if unless_result.return_code == 0:
                LOG.debug("'unless' for {} succeeded, not fixing".format(self.id))
                status_before.correct = True

        if status_before.correct or not status_before.fixable:
            status_after = copy(status_before)
        else:
            if not interactive:
                self.fix(status_before)
                status_after = self.get_status()
            else:
                question = wrap_question(
                    self.id,
                    self.ask(status_before),
                    _("Fix {}?").format(bold(self.id)),
                )
                if ask_interactively(question,
                                     interactive_default):
                    self.fix(status_before)
                    status_after = self.get_status()
                else:
                    status_after = copy(status_before)
                    status_after.aborted = True

        self.node.repo.hooks.item_apply_end(
            self.node.repo,
            self.node,
            self,
            duration=datetime.now() - start_time,
            status_before=status_before,
            status_after=status_after,
        )

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

    def get_auto_deps(self, items):
        """
        Return a list of item IDs this item should have dependencies on.

        Be very careful when using this. There are few circumstances
        where this is really necessary. Only use this if you really need
        to examine the actual list of items in order to figure out your
        dependencies.

        MAY be overridden by subclasses.
        """
        return []

    def get_status(self):
        """
        Returns an ItemStatus instance describing the current status of
        the item on the actual node. Must not be cached.

        MUST be overridden by subclasses.
        """
        raise NotImplementedError()

    def patch_attributes(self, attributes):
        """
        Allows an item to preprocess the attributes it is initialized
        with. Returns the modified attributes dictionary.

        MAY be overridden by subclasses.
        """
        return attributes

    def validate_attributes(self, attributes):
        """
        Raises BundleError if something is amiss with the user-specified
        attributes.

        SHOULD be overridden by subclasses.
        """
        pass

    @classmethod
    def validate_name(cls, bundle, name):
        """
        Raise BundleError if the given name is not valid (e.g. contains
        invalid characters for this kind of item.

        MAY be overridden by subclasses.
        """
        pass
