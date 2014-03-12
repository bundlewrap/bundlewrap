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
    'depends': [],
    'triggered': False,
    'triggers': [],
    'unless': "",
}
ITEM_CLASSES = {}
ITEM_CLASSES_LOADED = False


def unpickle_item_class(class_name, bundle, name, attributes, has_been_triggered):
    for item_class in bundle.node.repo.item_classes:
        if item_class.__name__ == class_name:
            return item_class(
                bundle,
                name,
                attributes,
                has_been_triggered=has_been_triggered,
                skip_validation=True,
            )
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
        info=None,
        skipped=False,
    ):
        self.skipped = skipped
        self.correct = correct
        self.description = description
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
    STATUS_OK = 1
    STATUS_FIXED = 2
    STATUS_FAILED = 3
    STATUS_SKIPPED = 4
    STATUS_ACTION_OK = 5
    STATUS_ACTION_FAILED = 6
    STATUS_ACTION_SKIPPED = 7

    def __init__(self, bundle, name, attributes, has_been_triggered=False, skip_validation=False):
        self.attributes = {}
        self.bundle = bundle
        self.has_been_triggered = has_been_triggered
        self.item_dir = join(bundle.bundle_dir, self.BUNDLE_ATTRIBUTE_NAME)
        self.name = name
        self.node = bundle.node

        if not skip_validation:
            self.validate_name(bundle, name)
            self._validate_attribute_names(bundle, self.id, attributes)
            self._validate_required_attributes(bundle, self.id, attributes)
            self.validate_attributes(bundle, self.id, attributes)

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
                self.has_been_triggered,
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
                    "duplicate definition of {item} in bundles '{bundle1}' and '{bundle2}'"
                ).format(
                    item=item.id,
                    bundle1=item.bundle.name,
                    bundle2=self.bundle.name,
                ))

    @classmethod
    def _validate_attribute_names(cls, bundle, item_id, attributes):
        invalid_attributes = set(attributes.keys()).difference(
            set(cls.ITEM_ATTRIBUTES.keys()).union(
                set(BUILTIN_ITEM_ATTRIBUTES.keys())
            ),
        )
        if invalid_attributes:
            raise BundleError(
                _("invalid attribute(s) for '{item}' in bundle '{bundle}': {attrs}").format(
                    item=item_id,
                    bundle=bundle.name,
                    attrs=", ".join(invalid_attributes),
                )
            )

    def _validate_required_attributes(cls, bundle, item_id, attributes):
        missing = []
        for attrname in cls.REQUIRED_ATTRIBUTES:
            if attrname not in attributes:
                missing.append(attrname)
        if missing:
            raise BundleError(_(
                "{item} in bundle '{bundle}' missing required attribute(s): {attrs}"
            ).format(
                item=item_id,
                bundle=bundle.name,
                attrs=", ".join(missing),
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
        status_code = None
        status_before = None
        status_after = None
        start_time = datetime.now()

        if self.triggered and not self.has_been_triggered:
            LOG.debug("skipping {} because it wasn't triggered".format(self.id))
            status_code = self.STATUS_SKIPPED

        if status_code is None:
            status_before = self.get_status()
            if self.unless and not status_before.correct:
                unless_result = self.node.run(self.unless, may_fail=True)
                if unless_result.return_code == 0:
                    LOG.debug("'unless' for {} succeeded, not fixing".format(self.id))
                    status_code = self.STATUS_SKIPPED

        if status_code is None:
            if status_before.correct:
                status_code = self.STATUS_OK

        if status_code is None:
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
                    status_code = self.STATUS_SKIPPED

        if status_code is None:
            if status_after.correct:
                status_code = self.STATUS_FIXED
            else:
                status_code = self.STATUS_FAILED

        self.node.repo.hooks.item_apply_end(
            self.node.repo,
            self.node,
            self,
            duration=datetime.now() - start_time,
            status_code=status_code,
            status_before=status_before,
            status_after=status_after,
        )

        return status_code

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

    def test(self):
        """
        Used by `bw repo test`. Should do as much as possible to detect
        what would become a runtime error during a `bw apply`. Files
        will attempt to render their templates for example.

        SHOULD be overridden by subclasses
        """
        pass

    @classmethod
    def validate_attributes(cls, bundle, item_id, attributes):
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
