"""
Note that modules in this package have to use absolute imports because
Repository.item_classes loads them as files.
"""
from copy import copy
from datetime import datetime
from inspect import cleandoc
from os.path import join
from textwrap import TextWrapper

from bundlewrap.exceptions import BundleError, ItemDependencyError, FaultUnavailable
from bundlewrap.utils import cached_property
from bundlewrap.utils.dicts import diff_keys, diff_value, hash_statedict, validate_statedict
from bundlewrap.utils.text import force_text, mark_for_translation as _
from bundlewrap.utils.text import blue, bold, italic, wrap_question
from bundlewrap.utils.ui import io
from bundlewrap.operations import run_local


BUILTIN_ITEM_ATTRIBUTES = {
    'cascade_skip': None,
    'comment': None,
    'needed_by': set(),
    'needs': set(),
    'preceded_by': set(),
    'precedes': set(),
    'error_on_missing_fault': False,
    'tags': set(),
    'triggered': False,
    'triggered_by': set(),
    'triggers': set(),
    'unless': "",
    'when_creating': {},
}

wrapper = TextWrapper(
    break_long_words=False,
    break_on_hyphens=False,
    expand_tabs=False,
    replace_whitespace=False,
)


def format_comment(comment):
    result = "\n\n"
    for line in wrapper.wrap(cleandoc(comment)):
        for inlineline in line.split("\n"):
            result += "{} {}\n".format(bold("#"), italic(inlineline))
    return result


class ItemStatus:
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


def make_normalize(attribute_default):
    """
    This is to ensure you can pass filter() results and such in place of
    lists and have them converted to the proper type automatically.
    """
    if type(attribute_default) in (dict, list, set, tuple):
        def normalize(attribute_value):
            if attribute_value is None:
                return attribute_value
            else:
                return type(attribute_default)(attribute_value)
        return normalize
    else:
        return copy


class Item:
    """
    A single piece of configuration (e.g. a file, a package, a service).
    """
    BUNDLE_ATTRIBUTE_NAME = None
    ITEM_ATTRIBUTES = {}
    ITEM_TYPE_NAME = None
    REQUIRED_ATTRIBUTES = []
    SKIP_REASON_CMDLINE = 1
    SKIP_REASON_DEP_FAILED = 2
    SKIP_REASON_FAULT_UNAVAILABLE = 3
    SKIP_REASON_INTERACTIVE = 4
    SKIP_REASON_INTERACTIVE_ONLY = 5
    SKIP_REASON_NO_TRIGGER = 6
    SKIP_REASON_SOFTLOCK = 7
    SKIP_REASON_UNLESS = 8
    SKIP_REASON_DEP_SKIPPED = 9
    SKIP_REASON_DESC = {
        SKIP_REASON_CMDLINE: _("cmdline"),
        SKIP_REASON_DEP_FAILED: _("dependency failed"),
        SKIP_REASON_FAULT_UNAVAILABLE: _("Fault unavailable"),
        SKIP_REASON_INTERACTIVE: _("declined interactively"),
        SKIP_REASON_INTERACTIVE_ONLY: _("interactive only"),
        SKIP_REASON_NO_TRIGGER: _("not triggered"),
        SKIP_REASON_SOFTLOCK: _("soft locked"),
        SKIP_REASON_UNLESS: _("unless"),
        SKIP_REASON_DEP_SKIPPED: _("dependency skipped"),
    }
    STATUS_OK = 1
    STATUS_FIXED = 2
    STATUS_FAILED = 3
    STATUS_SKIPPED = 4
    STATUS_ACTION_SUCCEEDED = 5
    WHEN_CREATING_ATTRIBUTES = {}

    @classmethod
    def block_concurrent(cls, node_os, node_os_version):
        """
        Return a list of item types that cannot be applied in parallel
        with this item type.
        """
        return []

    def __init__(
        self,
        bundle,
        name,
        attributes,
        skip_validation=False,
        skip_name_validation=False,
    ):
        self.attributes = {}
        self.bundle = bundle
        self.has_been_triggered = False
        self.item_dir = join(bundle.bundle_dir, self.BUNDLE_ATTRIBUTE_NAME)
        self.item_data_dir = join(bundle.bundle_data_dir, self.BUNDLE_ATTRIBUTE_NAME)
        self.name = name
        self.node = bundle.node
        self.when_creating = {}
        self._command_results = []
        self._faults_missing_for_attributes = set()
        self._precedes_items = set()

        if not skip_validation:
            if not skip_name_validation:
                self._validate_name(bundle, name)
                self.validate_name(bundle, name)
            self._validate_attribute_names(bundle, self.id, attributes)
            self._validate_required_attributes(bundle, self.id, attributes)
            self.validate_attributes(bundle, self.id, attributes)

        try:
            attributes = self.patch_attributes(attributes)
        except FaultUnavailable:
            self._faults_missing_for_attributes.add(_("unknown"))

        for attribute_name, attribute_default in BUILTIN_ITEM_ATTRIBUTES.items():
            normalize = make_normalize(attribute_default)
            try:
                setattr(self, attribute_name, force_text(normalize(attributes.get(
                    attribute_name,
                    copy(attribute_default),
                ))))
            except FaultUnavailable:
                self._faults_missing_for_attributes.add(attribute_name)
                setattr(self, attribute_name, BUILTIN_ITEM_ATTRIBUTES[attribute_name])

        for attribute_name, attribute_default in self.ITEM_ATTRIBUTES.items():
            if attribute_name not in BUILTIN_ITEM_ATTRIBUTES:
                normalize = make_normalize(attribute_default)
                try:
                    self.attributes[attribute_name] = force_text(normalize(attributes.get(
                        attribute_name,
                        copy(attribute_default),
                    )))
                except FaultUnavailable:
                    self._faults_missing_for_attributes.add(attribute_name)

        for attribute_name, attribute_default in self.WHEN_CREATING_ATTRIBUTES.items():
            normalize = make_normalize(attribute_default)
            try:
                self.when_creating[attribute_name] = force_text(normalize(
                    attributes.get('when_creating', {}).get(
                        attribute_name,
                        copy(attribute_default),
                    )
                ))
            except FaultUnavailable:
                self._faults_missing_for_attributes.add('when_creating/' + attribute_name)

        if self.cascade_skip is None:
            self.cascade_skip = not (self.unless or self.triggered)

        if self.id in self.triggers:
            raise BundleError(_(
                "item {item} in bundle '{bundle}' can't trigger itself"
            ).format(
                bundle=self.bundle.name,
                item=self.id,
            ))

    def __eq__(self, other):
        return self.id == other.id

    def __hash__(self):
        return hash(self.id)

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

    def _check_loopback_dependency(self):
        """
        Alerts the user if they have an item depend on itself.
        """
        if self.id in self.needs or self.id in self.needed_by:
            raise ItemDependencyError(_(
                "'{item}' in bundle '{bundle}' on node '{node}' cannot depend on itself"
            ).format(
                item=self.id,
                bundle=self.bundle.name,
                node=self.node.name,
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
        """
        Returns True if 'unless' wants to skip this item.
        """
        if self.unless and (self.ITEM_TYPE_NAME == 'action' or not self.cached_status.correct):
            unless_result = self.node.run(self.unless, may_fail=True)
            return unless_result.return_code == 0
        else:
            return False

    def _triggers_preceding_items(self, interactive=False):
        """
        Preceding items will execute this to figure out if they're
        triggered.
        """
        if self.cached_unless_result:
            # 'unless' says we don't need to run
            return False
        if self.ITEM_TYPE_NAME == 'action':
            # so we have an action where 'unless' says it must be run
            # but the 'interactive' attribute might still override that
            if self.attributes['interactive'] and not interactive:
                return False
            else:
                return True
        return not self.cached_status.correct

    def _raise_for_faults(self):
        raise FaultUnavailable(_(
            "{item} on {node} is missing faults "
            "for these attributes: {attrs} "
            "(most of the time this means you're missing "
            "a required key in your .secrets.cfg)"
        ).format(
            attrs=", ".join(sorted(self._faults_missing_for_attributes)),
            item=self.id,
            node=self.node.name,
        ))

    def _skip_with_soft_locks(self, mine, others):
        """
        Returns True/False depending on whether the item should be
        skipped based on the given set of locks.
        """
        for lock in mine:
            if self.covered_by_autoskip_selector(lock['items']):
                io.debug(_("{item} on {node} whitelisted by lock {lock}").format(
                    item=self.id,
                    lock=lock['id'],
                    node=self.node.name,
                ))
                return False
        for lock in others:
            if self.covered_by_autoskip_selector(lock['items']):
                io.debug(_("{item} on {node} blacklisted by lock {lock}").format(
                    item=self.id,
                    lock=lock['id'],
                    node=self.node.name,
                ))
                return True
        return False

    def _test(self):
        with io.job(_("{node}  {bundle}  {item}").format(
            bundle=bold(self.bundle.name),
            item=self.id,
            node=bold(self.node.name),
        )):
            if self._faults_missing_for_attributes:
                self._raise_for_faults()
            return self.test()

    @classmethod
    def _validate_attribute_names(cls, bundle, item_id, attributes):
        if not isinstance(attributes, dict):
            raise BundleError(_(
                "invalid item '{item}' in bundle '{bundle}': not a dict"
            ).format(
                item=item_id,
                bundle=bundle.name,
            ))
        invalid_attributes = set(attributes.keys()).difference(
            set(cls.ITEM_ATTRIBUTES.keys()).union(
                set(BUILTIN_ITEM_ATTRIBUTES.keys())
            ),
        )
        if invalid_attributes:
            raise BundleError(_(
                "invalid attribute(s) for '{item}' in bundle '{bundle}': {attrs}"
            ).format(
                item=item_id,
                bundle=bundle.name,
                attrs=", ".join(invalid_attributes),
            ))

        invalid_attributes = set(attributes.get('when_creating', {}).keys()).difference(
            set(cls.WHEN_CREATING_ATTRIBUTES.keys())
        )
        if invalid_attributes:
            raise BundleError(_(
                "invalid when_creating attribute(s) for '{item}' in bundle '{bundle}': {attrs}"
            ).format(
                item=item_id,
                bundle=bundle.name,
                attrs=", ".join(invalid_attributes),
            ))

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

    @classmethod
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
        autoskip_selector=[],
        autoonly_selector=[],
        my_soft_locks=(),
        other_peoples_soft_locks=(),
        interactive=False,
        interactive_default=True,
        show_diff=True,
    ):
        self.node.repo.hooks.item_apply_start(
            self.node.repo,
            self.node,
            self,
        )
        status_code = None
        status_before = None
        status_after = None
        details = None
        start_time = datetime.now()

        if not self.covered_by_autoonly_selector(autoonly_selector):
            io.debug(_(
                "autoonly does not match {item} on {node}"
            ).format(item=self.id, node=self.node.name))
            status_code = self.STATUS_SKIPPED
            details = self.SKIP_REASON_CMDLINE

        if self.covered_by_autoskip_selector(autoskip_selector):
            io.debug(_(
                "autoskip matches {item} on {node}"
            ).format(item=self.id, node=self.node.name))
            status_code = self.STATUS_SKIPPED
            details = self.SKIP_REASON_CMDLINE

        if self._skip_with_soft_locks(my_soft_locks, other_peoples_soft_locks):
            status_code = self.STATUS_SKIPPED
            details = self.SKIP_REASON_SOFTLOCK

        for item in self._precedes_items:
            if item._triggers_preceding_items(interactive=interactive):
                io.debug(_(
                    "preceding item {item} on {node} has been triggered by {other_item}"
                ).format(item=self.id, node=self.node.name, other_item=item.id))
                self.has_been_triggered = True
                break
            else:
                io.debug(_(
                    "preceding item {item} on {node} has NOT been triggered by {other_item}"
                ).format(item=self.id, node=self.node.name, other_item=item.id))

        if self.triggered and not self.has_been_triggered and status_code is None:
            io.debug(_(
                "skipping {item} on {node} because it wasn't triggered"
            ).format(item=self.id, node=self.node.name))
            status_code = self.STATUS_SKIPPED
            details = self.SKIP_REASON_NO_TRIGGER

        if status_code is None and self.cached_unless_result and status_code is None:
            io.debug(_(
                "'unless' for {item} on {node} succeeded, not fixing"
            ).format(item=self.id, node=self.node.name))
            status_code = self.STATUS_SKIPPED
            details = self.SKIP_REASON_UNLESS

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
                    attrs=", ".join(sorted(self._faults_missing_for_attributes)),
                    item=self.id,
                    node=self.node.name,
                ))
                status_code = self.STATUS_SKIPPED
                details = self.SKIP_REASON_FAULT_UNAVAILABLE

        if status_code is None:
            try:
                status_before = self.cached_status
            except FaultUnavailable:
                if self.error_on_missing_fault:
                    self._raise_for_faults()
                else:
                    io.debug(_(
                        "skipping {item} on {node} because it is missing Faults "
                        "(most of the time this means you're missing "
                        "a required key in your .secrets.cfg)"
                    ).format(
                        item=self.id,
                        node=self.node.name,
                    ))
                    status_code = self.STATUS_SKIPPED
                    details = self.SKIP_REASON_FAULT_UNAVAILABLE
            else:
                if status_before.correct:
                    status_code = self.STATUS_OK
                elif show_diff or interactive:
                    if status_before.must_be_created:
                        details = self.display_on_create(copy(status_before.cdict))
                    elif status_before.must_be_deleted:
                        details = self.display_on_delete(copy(status_before.sdict))
                    else:
                        details = self.display_dicts(
                            copy(status_before.cdict),
                            copy(status_before.sdict),
                            # TODO remove sorted() in 5.0 to pass a set
                            sorted(copy(status_before.keys_to_fix)),
                        )

        if status_code is None:
            if not interactive:
                with io.job(_("{node}  {bundle}  {item}").format(
                    bundle=bold(self.bundle.name),
                    item=self.id,
                    node=bold(self.node.name),
                )):
                    self.fix(status_before)
            else:
                if status_before.must_be_created:
                    question_text = "\n".join(
                        f"{bold(key)}  {value}"
                        for key, value in sorted(details.items())
                    )
                    prompt = _("Create {}?").format(bold(self.id))
                elif status_before.must_be_deleted:
                    question_text = "\n".join(
                        f"{bold(key)}  {value}"
                        for key, value in sorted(details.items())
                    )
                    prompt = _("Delete {}?").format(bold(self.id))
                else:
                    display_cdict, display_sdict, display_keys_to_fix = details
                    question_text = "\n".join(
                        diff_value(
                            key,
                            display_sdict[key],
                            display_cdict[key],
                        )
                        for key in sorted(display_keys_to_fix)
                    )
                    prompt = _("Fix {}?").format(bold(self.id))
                if self.comment:
                    question_text += format_comment(self.comment)
                question = wrap_question(
                    self.id,
                    question_text,
                    prompt,
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
                    with io.job(_("{node}  {bundle}  {item}").format(
                        bundle=bold(self.bundle.name),
                        item=self.id,
                        node=bold(self.node.name),
                    )):
                        self.fix(status_before)
                else:
                    status_code = self.STATUS_SKIPPED
                    details = self.SKIP_REASON_INTERACTIVE

        if status_code is None:
            status_after = self.get_status(cached=False)
            status_code = self.STATUS_FIXED if status_after.correct else self.STATUS_FAILED

        self.node.repo.hooks.item_apply_end(
            self.node.repo,
            self.node,
            self,
            duration=datetime.now() - start_time,
            status_code=status_code,
            status_before=status_before,
            status_after=status_after,
        )
        return (
            status_code,
            details,
            status_before.must_be_created if status_before else None,
            status_before.must_be_deleted if status_before else None,
        )

    def run_local(self, command, **kwargs):
        result = run_local(command, **kwargs)
        self._command_results.append({
            'command': command,
            'result': result,
        })
        return result

    def run(self, command, **kwargs):
        result = self.node.run(command, **kwargs)
        self._command_results.append({
            'command': command,
            'result': result,
        })
        return result

    def cdict(self):
        """
        Return a statedict that describes the target state of this item
        as configured in the repo. Returning `None` instead means that
        the item should not exist.

        MAY be overridden by subclasses.
        """
        return self.attributes

    def covered_by_autoskip_selector(self, autoskip_selector):
        """
        True if this item should be skipped based on the given selector
        string (e.g. "tag:foo,bundle:bar").
        """
        components = [c.strip() for c in autoskip_selector]
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

    def covered_by_autoonly_selector(self, autoonly_selector):
        """
        True if this item should be NOT skipped based on the given selector
        string (e.g. "tag:foo,bundle:bar").
        """
        if not autoonly_selector:
            return True
        components = [c.strip() for c in autoonly_selector]
        if (
            self.id in components or
            "bundle:{}".format(self.bundle.name) in components or
            "{}:".format(self.ITEM_TYPE_NAME) in components
        ):
            return True
        for tag in self.tags:
            if "tag:{}".format(tag) in components:
                return True
        for depending_item in self._incoming_deps:
            if (
                depending_item.id in components or
                "bundle:{}".format(depending_item.bundle.name) in components or
                "{}:".format(depending_item.ITEM_TYPE_NAME) in components
            ):
                return True
            for tag in depending_item.tags:
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
        with io.job(_("{node}  {bundle}  {item}").format(
            bundle=bold(self.bundle.name),
            item=self.id,
            node=bold(self.node.name),
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

    def verify(self):
        if self.cached_status.must_be_created:
            display = self.display_on_create(copy(self.cached_status.cdict))
        elif self.cached_status.must_be_deleted:
            display = self.display_on_delete(copy(self.cached_status.sdict))
        else:
            display = self.display_dicts(
                copy(self.cached_status.cdict),
                copy(self.cached_status.sdict),
                # TODO remove sorted() in 5.0 to pass a set
                sorted(copy(self.cached_status.keys_to_fix)),
            )
        return self.cached_unless_result, self.cached_status, display

    def display_on_create(self, cdict):
        """
        Given a cdict as implemented above, modify it to better suit
        interactive presentation when an item is created.

        MAY be overridden by subclasses.
        """
        return cdict

    # TODO rename to display_on_fix in 5.0
    def display_dicts(self, cdict, sdict, keys):
        """
        Given cdict and sdict as implemented above, modify them to
        better suit interactive presentation. The keys parameter is a
        list of keys whose values differ between cdict and sdict.

        MAY be overridden by subclasses.
        """
        return (cdict, sdict, keys)

    def display_on_delete(self, sdict):
        """
        Given an sdict as implemented above, modify it to better suit
        interactive presentation when an item is deleted.

        MAY be overridden by subclasses.
        """
        return sdict

    def patch_attributes(self, attributes):
        """
        Allows an item to preprocess the attributes it is initialized
        with. Returns the modified attributes dictionary.

        MAY be overridden by subclasses.
        """
        return attributes

    def preview(self):
        """
        Can return a preview of this item as a Unicode string.
        BundleWrap will NOT add a trailing newline.

        MAY be overridden by subclasses.
        """
        raise NotImplementedError()

    def sdict(self):
        """
        Return a statedict that describes the actual state of this item
        on the node. Returning `None` instead means that the item does
        not exist on the node.

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
