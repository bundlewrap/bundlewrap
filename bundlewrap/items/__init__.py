# -*- coding: utf-8 -*-
"""
Note that modules in this package have to use absolute imports because
Repository.item_classes loads them as files.
"""
from __future__ import unicode_literals
from copy import copy
from datetime import datetime
from os.path import join

from bundlewrap.exceptions import BundleError, FaultUnavailable
from bundlewrap.utils import cached_property
from bundlewrap.utils.statedict import diff_keys, diff_value, hash_statedict, validate_statedict
from bundlewrap.utils.text import force_text, mark_for_translation as _
from bundlewrap.utils.text import blue, bold, wrap_question
from bundlewrap.utils.ui import io

BUILTIN_ITEM_ATTRIBUTES = {
    'cascade_skip': None,
    'needed_by': [],
    'needs': [],
    'preceded_by': [],
    'precedes': [],
    'error_on_missing_fault': False,
    'tags': [],
    'triggered': False,
    'triggered_by': [],
    'triggers': [],
    'unless': "",
}


class ItemStatus(object):
    """
    Holds information on a particular Item such as whether it needs
    fixing and what's broken.
    """

    def __init__(self, cdict, sdict):
        self.cdict = cdict
        self.sdict = sdict
        self.keys_to_fix = []
        self.must_be_deleted = (self.sdict is not None and self.cdict is None)
        self.must_be_created = (self.cdict is not None and self.sdict is None)
        if not self.must_be_deleted and not self.must_be_created:
            self.keys_to_fix = diff_keys(cdict, sdict)

    def __repr__(self):
        return "<ItemStatus correct:{}>".format(self.correct)

    @property
    def correct(self):
        return not self.must_be_deleted and not self.must_be_created and not bool(self.keys_to_fix)


class Item(object):
    """
    A single piece of configuration (e.g. a file, a package, a service).
    """
    BINARY_ATTRIBUTES = []
    BLOCK_CONCURRENT = []
    BUNDLE_ATTRIBUTE_NAME = None
    ITEM_ATTRIBUTES = {}
    ITEM_TYPE_NAME = None
    REQUIRED_ATTRIBUTES = []
    STATUS_OK = 1
    STATUS_FIXED = 2
    STATUS_FAILED = 3
    STATUS_SKIPPED = 4
    STATUS_ACTION_SUCCEEDED = 5

    def __init__(
        self,
        bundle,
        name,
        attributes,
        faults_missing_for_attributes=None,
        has_been_triggered=False,
        skip_validation=False,
        skip_name_validation=False,
    ):
        self.attributes = {}
        self.bundle = bundle
        self.has_been_triggered = has_been_triggered
        self.item_dir = join(bundle.bundle_dir, self.BUNDLE_ATTRIBUTE_NAME)
        self.item_data_dir = join(bundle.bundle_data_dir, self.BUNDLE_ATTRIBUTE_NAME)
        self.name = name
        self.node = bundle.node
        self._faults_missing_for_attributes = [] if faults_missing_for_attributes is None \
            else faults_missing_for_attributes
        self._precedes_items = []

        if not skip_validation:
            if not skip_name_validation:
                self._validate_name(bundle, name)
                self.validate_name(bundle, name)
            self._validate_attribute_names(bundle, self.id, attributes)
            self._validate_required_attributes(bundle, self.id, attributes)
            self.validate_attributes(bundle, self.id, attributes)

        attributes = self.patch_attributes(attributes)

        for attribute_name, attribute_default in \
                BUILTIN_ITEM_ATTRIBUTES.items():
            setattr(self, attribute_name, force_text(attributes.get(
                attribute_name,
                copy(attribute_default),
            )))

        for attribute_name, attribute_default in \
                self.ITEM_ATTRIBUTES.items():
            if attribute_name not in BUILTIN_ITEM_ATTRIBUTES:
                try:
                    self.attributes[attribute_name] = force_text(attributes.get(
                        attribute_name,
                        attribute_default,
                    ))
                except FaultUnavailable:
                    self._faults_missing_for_attributes.append(attribute_name)

        if self.cascade_skip is None:
            self.cascade_skip = not (self.unless or self.triggered)

        if self.id in self.triggers:
            raise BundleError(_(
                "item {item} in bundle '{bundle}' can't trigger itself"
            ).format(
                bundle=self.bundle.name,
                item=self.id,
            ))

    def __lt__(self, other):
        return self.id < other.id

    def __str__(self):
        return self.id

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

    def _check_redundant_dependencies(self):
        """
        Alerts the user if they have defined a redundant dependency
        (such as settings 'needs' on a triggered item pointing to the
        triggering item).
        """
        for dep in self._deps:
            if self._deps.count(dep) > 1:
                raise BundleError(_(
                    "redundant dependency of {item1} in bundle '{bundle}' on {item2}"
                ).format(
                    bundle=self.bundle.name,
                    item1=self.id,
                    item2=dep,
                ))

    @cached_property
    def cached_cdict(self):
        if self._faults_missing_for_attributes:
            self._raise_for_faults()

        cdict = self.cdict()
        try:
            validate_statedict(cdict)
        except ValueError as e:
            raise ValueError(_(
                "{item} from bundle '{bundle}' returned invalid cdict: {msg}"
            ).format(
                bundle=self.bundle.name,
                item=self.id,
                msg=repr(e),
            ))
        return cdict

    @cached_property
    def cached_sdict(self):
        status = self.sdict()
        try:
            validate_statedict(status)
        except ValueError as e:
            raise ValueError(_(
                "{item} from bundle '{bundle}' returned invalid status: {msg}"
            ).format(
                bundle=self.bundle.name,
                item=self.id,
                msg=repr(e),
            ))
        return status

    @cached_property
    def cached_status(self):
        return self.get_status()

    @cached_property
    def cached_unless_result(self):
        if self.unless and not self.cached_status.correct:
            unless_result = self.node.run(self.unless, may_fail=True)
            return unless_result.return_code == 0
        else:
            return False

    def _precedes_incorrect_item(self, interactive=False):
        """
        Returns True if this item precedes another and the triggering
        item is in need of fixing.
        """
        for item in self._precedes_items:
            if item._precedes_incorrect_item():
                return True
        if self.cached_unless_result:
            # triggering item failed unless, so there is nothing to do
            return False
        if self.ITEM_TYPE_NAME == 'action':
            if self.attributes['interactive'] != interactive or \
                    self.attributes['interactive'] is None:
                return False
            else:
                return True
        return not self.cached_status.correct

    def _prepare_deps(self, items):
        # merge automatic and user-defined deps
        self._deps = list(self.needs) + list(self.get_auto_deps(items))

    def _raise_for_faults(self):
        raise FaultUnavailable(_(
            "{item} on {node} is missing faults "
            "for these attributes: {attrs} "
            "(most of the time this means you're missing "
            "a required key in your .secrets.cfg)"
        ).format(
            attrs=", ".join(self._faults_missing_for_attributes),
            item=self.id,
            node=self.node.name,
        ))

    def _skip_with_soft_locks(self, mine, others):
        """
        Returns True/False depending on whether the item should be
        skipped based on the given set of locks.
        """
        for lock in mine:
            for selector in lock['items']:
                if self.covered_by_autoskip_selector(selector):
                    io.debug(_("{item} on {node} whitelisted by lock {lock}").format(
                        item=self.id,
                        lock=lock['id'],
                        node=self.node.name,
                    ))
                    return False
        for lock in others:
            for selector in lock['items']:
                if self.covered_by_autoskip_selector(selector):
                    io.debug(_("{item} on {node} blacklisted by lock {lock}").format(
                        item=self.id,
                        lock=lock['id'],
                        node=self.node.name,
                    ))
                    return True
        return False

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

    @classmethod
    def _validate_name(cls, bundle, name):
        if ":" in name:
            raise BundleError(_(
                "invalid name for {type} in bundle '{bundle}': {name} (must not contain colon)"
            ).format(
                bundle=bundle.name,
                name=name,
                type=cls.ITEM_TYPE_NAME,
            ))

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

    def apply(
        self,
        autoskip_selector="",
        my_soft_locks=(),
        other_peoples_soft_locks=(),
        interactive=False,
        interactive_default=True,
    ):
        self.node.repo.hooks.item_apply_start(
            self.node.repo,
            self.node,
            self,
        )
        keys_to_fix = None
        status_code = None
        status_before = None
        status_after = None
        start_time = datetime.now()

        if self.covered_by_autoskip_selector(autoskip_selector):
            io.debug(_(
                "autoskip matches {item} on {node}"
            ).format(item=self.id, node=self.node.name))
            status_code = self.STATUS_SKIPPED
            keys_to_fix = [_("cmdline")]

        if self._skip_with_soft_locks(my_soft_locks, other_peoples_soft_locks):
            status_code = self.STATUS_SKIPPED
            keys_to_fix = [_("soft locked")]

        if self.triggered and not self.has_been_triggered and status_code is None:
            io.debug(_(
                "skipping {item} on {node} because it wasn't triggered"
            ).format(item=self.id, node=self.node.name))
            status_code = self.STATUS_SKIPPED
            keys_to_fix = [_("not triggered")]

        if status_code is None and self.cached_unless_result and status_code is None:
            io.debug(_(
                "'unless' for {item} on {node} succeeded, not fixing"
            ).format(item=self.id, node=self.node.name))
            status_code = self.STATUS_SKIPPED
            keys_to_fix = ["unless"]

        if self._faults_missing_for_attributes and status_code is None:
            if self.error_on_missing_fault:
                self._raise_for_faults()
            else:
                io.debug(_(
                    "skipping {item} on {node} because it is missing faults "
                    "for these attributes: {attrs} "
                    "(most of the time this means you're missing "
                    "a required key in your .secrets.cfg)"
                ).format(
                    attrs=", ".join(self._faults_missing_for_attributes),
                    item=self.id,
                    node=self.node.name,
                ))
                status_code = self.STATUS_SKIPPED
                keys_to_fix = [_("unavailable")]

        if status_code is None:
            try:
                status_before = self.cached_status
            except FaultUnavailable:
                if self.error_on_missing_fault:
                    self._raise_for_faults()
                else:
                    io.debug(_(
                        "skipping {item} on {node} because it is missing faults "
                        "in a template "
                        "(most of the time this means you're missing "
                        "a required key in your .secrets.cfg)"
                    ).format(
                        item=self.id,
                        node=self.node.name,
                    ))
                    status_code = self.STATUS_SKIPPED
                    keys_to_fix = [_("unavailable")]
            else:
                if status_before.correct:
                    status_code = self.STATUS_OK

        if status_code is None:
            keys_to_fix = self.display_keys(
                copy(self.cached_cdict),
                copy(status_before.sdict),
                status_before.keys_to_fix[:],
            )
            if not interactive:
                with io.job(_("  {node}  {bundle}  {item}  fixing...").format(
                    bundle=self.bundle.name,
                    item=self.id,
                    node=self.node.name,
                )):
                    self.fix(status_before)
            else:
                if status_before.must_be_created:
                    question_text = _("Doesn't exist. Will be created.")
                elif status_before.must_be_deleted:
                    question_text = _("Found on node. Will be removed.")
                else:
                    cdict, sdict = self.display_dicts(
                        copy(self.cached_cdict),
                        copy(status_before.sdict),
                        keys_to_fix,
                    )
                    question_text = self.ask(cdict, sdict, keys_to_fix)
                question = wrap_question(
                    self.id,
                    question_text,
                    _("Fix {}?").format(bold(self.id)),
                    prefix="{x} {node} ".format(
                        node=bold(self.node.name),
                        x=blue("?"),
                    ),
                )
                answer = io.ask(
                    question,
                    interactive_default,
                    epilogue="{x} {node}".format(
                        node=bold(self.node.name),
                        x=blue("?"),
                    ),
                )
                if answer:
                    with io.job(_("  {node}  {bundle}  {item}  fixing...").format(
                        bundle=self.bundle.name,
                        item=self.id,
                        node=self.node.name,
                    )):
                        self.fix(status_before)
                else:
                    status_code = self.STATUS_SKIPPED
                    keys_to_fix = [_("interactive")]

        if status_code is None:
            status_after = self.get_status(cached=False)
            status_code = self.STATUS_FIXED if status_after.correct else self.STATUS_FAILED

        if status_code == self.STATUS_SKIPPED:
            # can't use else for this because status_before is None
            changes = keys_to_fix
        elif status_before.must_be_created:
            changes = True
        elif status_before.must_be_deleted:
            changes = False
        elif status_code == self.STATUS_FAILED:
            changes = self.display_keys(
                self.cached_cdict.copy(),
                status_after.sdict.copy(),
                status_after.keys_to_fix[:],
            )
        else:
            changes = keys_to_fix

        self.node.repo.hooks.item_apply_end(
            self.node.repo,
            self.node,
            self,
            duration=datetime.now() - start_time,
            status_code=status_code,
            status_before=status_before,
            status_after=status_after,
        )
        return (status_code, changes)

    def ask(self, status_should, status_actual, relevant_keys):
        """
        Returns a string asking the user if this item should be
        implemented.
        """
        result = []
        for key in relevant_keys:
            result.append(diff_value(key, status_actual[key], status_should[key]))
        return "\n\n".join(result)

    def cdict(self):
        """
        Return a statedict that describes the target state of this item
        as configured in the repo. An empty dict means that the item
        should not exist.

        MAY be overridden by subclasses.
        """
        return self.attributes

    def covered_by_autoskip_selector(self, autoskip_selector):
        """
        True if this item should be skipped based on the given selector
        string (e.g. "tag:foo,bundle:bar").
        """
        components = [c.strip() for c in autoskip_selector.split(",")]
        if (
            "*" in components or
            self.id in components or
            "bundle:{}".format(self.bundle.name) in components or
            "{}:".format(self.ITEM_TYPE_NAME) in components
        ):
            return True
        for tag in self.tags:
            if "tag:{}".format(tag) in components:
                return True
        return False

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

    def get_canned_actions(self):
        """
        Return a dictionary of action definitions (mapping action names
        to dicts of action attributes, as in bundles).

        MAY be overridden by subclasses.
        """
        return {}

    def get_status(self, cached=True):
        """
        Returns an ItemStatus instance describing the current status of
        the item on the actual node.
        """
        with io.job(_("  {node}  {bundle}  {item}  checking...").format(
            bundle=self.bundle.name,
            item=self.id,
            node=self.node.name,
        )):
            if not cached:
                del self._cache['cached_sdict']
            return ItemStatus(self.cached_cdict, self.cached_sdict)

    def hash(self):
        return hash_statedict(self.cached_cdict)

    @property
    def id(self):
        if self.ITEM_TYPE_NAME == 'action' and ":" in self.name:
            # canned actions don't have an "action:" prefix
            return self.name
        return "{}:{}".format(self.ITEM_TYPE_NAME, self.name)

    def display_dicts(self, cdict, sdict, keys):
        """
        Given cdict and sdict as implemented above, modify them to
        better suit interactive presentation. The keys parameter is the
        return value of display_keys (see below) and provided for
        reference only.

        MAY be overridden by subclasses.
        """
        return (cdict, sdict)

    def display_keys(self, cdict, sdict, keys):
        """
        Given a list of keys whose values differ between cdict and
        sdict, modify them to better suit presentation to the user.

        MAY be overridden by subclasses.
        """
        return keys

    def patch_attributes(self, attributes):
        """
        Allows an item to preprocess the attributes it is initialized
        with. Returns the modified attributes dictionary.

        MAY be overridden by subclasses.
        """
        return attributes

    def sdict(self):
        """
        Return a statedict that describes the actual state of this item
        on the node. An empty dict means that the item does not exist
        on the node.

        For the item to validate as correct, the values for all keys in
        self.cdict() have to match this statedict.

        MUST be overridden by subclasses.
        """
        raise NotImplementedError()

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
