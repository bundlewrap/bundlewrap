from contextlib import suppress

from .exceptions import BundleError, ItemDependencyError, NoSuchItem
from .items import ALLOWED_ITEM_AUTO_ATTRIBUTES, Item
from .items.actions import Action
from .utils.plot import explain_item_dependency_loop
from .utils.text import bold, mark_for_translation as _
from .utils.ui import io


class ItemDependencyLoop(ItemDependencyError):
    """
    Raised when there is a loop in item dependencies.
    """
    def __init__(self, items):
        self.items = items

    def __repr__(self):
        return "<ItemDependencyLoop between {} items>".format(len(self.items))

    def __str__(self):
        return "\n".join(explain_item_dependency_loop(self.items))


class TagFillerItem(Item):
    BUNDLE_ATTRIBUTE_NAME = "__tagfiller__"
    ITEM_TYPE_NAME = "empty_tag"

    def sdict(self):
        return {}


def resolve_selector(selector, items, originating_item_id=None, originating_tag=None):
    """
    Given an item selector (e.g. 'bundle:foo' or 'file:/bar'), return
    all items matching that selector from the given list of items.
    """
    if selector.startswith("!"):
        negate = lambda b: not b
        selector = selector[1:]
    else:
        negate = lambda b: b
    try:
        selector_type, selector_name = selector.split(":", 1)
    except ValueError:
        raise ValueError(_("invalid item selector: {}").format(selector))

    if selector_type == "bundle":
        return filter(
            lambda item:
                negate(item.bundle.name == selector_name) and
                item.id != originating_item_id,
            items,
        )
    elif selector_type == "tag":
        if not selector_name:  # "tag:"
            return filter(
                lambda item: negate(bool(item.tags)) and originating_tag not in item.tags,
                items,
            )
        else:
            return filter(
                lambda item: negate(selector_name in item.tags) and item.id != originating_item_id,
                items,
            )
    elif not selector_name:  # "file:"
        return filter(
            lambda item:
                negate(item.ITEM_TYPE_NAME == selector_type) and
                item.id != originating_item_id,
            items,
        )
    else:  # single item
        if negate(False):
            return filter(lambda item: item.id != selector, items)
        else:
            return [find_item(selector, items)]


def find_item(item_id, items):
    """
    Returns the first item with the given ID within the given list of
    items.
    """
    try:
        item = list(filter(lambda item: item.id == item_id, items))[0]
    except IndexError:
        raise NoSuchItem(_("item not found: {}").format(item_id))
    return item


def _flatten_dependencies(items):
    """
    This will cause all dependencies - direct AND inherited - to be
    listed in item._flattened_deps.
    """
    for item in items:
        if not hasattr(item, '_flattened_deps'):
            _flatten_deps_for_item(item, items)


def _flatten_deps_for_item(item, items):
    """
    Recursively retrieves and returns a list of all inherited
    dependencies of the given item.

    This can handle loops, but will ignore them.
    """
    item._flattened_deps = {item.id for item in item._deps}
    item._flattened_deps_needs = {item.id for item in item._deps_needs | item._deps_needed_by}

    for dep_item in item._deps:
        # Don't recurse if we have already resolved nested
        # dependencies for this item. Also serves as a guard
        # against infinite recursion when there are loops.
        if not hasattr(dep_item, '_flattened_deps'):
            _flatten_deps_for_item(dep_item, items)

        item._flattened_deps.update(dep_item._flattened_deps)
        item._flattened_deps_needs.update(dep_item._flattened_deps_needs)


def _add_incoming_needs(items):
    """
    For each item, records all items that need that item in
    ._incoming_needs.
    """
    mapping = {}
    for item in items:
        for other_item_id in item._flattened_deps_needs:
            mapping.setdefault(other_item_id, set())
            mapping[other_item_id].add(item)

    for item in items:
        item._incoming_needs = mapping.get(item.id, set())


def _prepare_auto_attrs(items):
    for item in items:
        auto_attrs = item.get_auto_attrs(items)
        # remove next line in 5.0 when killing get_auto_deps
        auto_attrs['needs'] = set(auto_attrs.get('needs', set())) | set(item.get_auto_deps(items))
        for key, value in auto_attrs.items():
            if key not in ALLOWED_ITEM_AUTO_ATTRIBUTES:
                raise ValueError(_("get_auto_attrs() on {item} returned illegal key {key}").format(
                    item=item.id,
                    key=repr(key),
                ))
            setattr(item, key, set(getattr(item, key)) | set(value))


def _prepare_deps(items):
    selector_cache = {}

    for item in items:
        item._deps = set()  # holds all item ids blocking execution of that item
        for dep_type, deps in (
            ('after', set(item.after)),
            ('needs', set(item.needs)),
        ):
            setattr(item, '_deps_' + dep_type, set())
            for dep in deps:
                try:
                    resolved_deps = selector_cache[dep]
                except KeyError:
                    try:
                        resolved_deps = tuple(resolve_selector(dep, items))
                    except NoSuchItem:
                        raise ItemDependencyError(_(
                            "'{item}' in bundle '{bundle}' has a dependency ({dep_type}) "
                            "on '{dep}', which doesn't exist"
                        ).format(
                            item=item.id,
                            bundle=item.bundle.name,
                            dep=dep,
                            dep_type=dep_type,
                        ))

                    selector_cache[dep] = resolved_deps

                # Don't put the item itself into its own deps.
                resolved_deps = tuple(filter(lambda i: i.id != item.id, resolved_deps))

                item._deps.update(resolved_deps)
                getattr(item, '_deps_' + dep_type).update(resolved_deps)


def _inject_canned_actions(items):
    """
    Looks for canned actions like "svc_upstart:mysql:reload" in items,
    created actions for them and add those to the list of items.
    """
    actions = set()
    for item in items:
        for canned_action_name, canned_action_attrs in item.get_canned_actions().items():
            canned_action_id = f"{item.id}:{canned_action_name}"
            canned_action_attrs.update({'triggered': True})
            action = Action(
                item.bundle,
                canned_action_id,
                canned_action_attrs,
                skip_name_validation=True,
            )
            actions.add(action)
    items.update(actions)


def _inject_tag_filler_items(items, bundles):
    """
    Creates TagFillerItems to ensure each tag has at least one item.
    This is important so even if there are no user-defined items with
    a tag, that tag can still be used to chain dependencies.

        [item:A] --needs--> [tag:B] --needs--> [item:C]

    Users will assume that item:A will implicitly depend on item:C, but
    if tag:B doesn't resolve to any items, that connection won't be
    made.
    """
    for bundle in bundles:
        for tag, attrs in bundle.bundle_attrs.get('tags', {}).items():
            if not tuple(resolve_selector(f"tag:{tag}", items)):
                items.add(TagFillerItem(bundle, tag, {'tags': {tag}}))


def _inject_reverse_dependencies(items):
    """
    Looks for 'before' and 'needed_by' deps and creates standard 
    dependencies accordingly.
    """
    for item in items:
        for dep_type in ('before', 'needed_by'):
            setattr(item, '_deps_' + dep_type, set())

    for item in items:
        for dep_type in ('before', 'needed_by'):
            for depending_item_id in set(getattr(item, dep_type)):
                try:
                    dependent_items = resolve_selector(
                        depending_item_id,
                        items,
                        originating_item_id=item.id,
                    )
                except NoSuchItem:
                    raise ItemDependencyError(_(
                        "'{item}' in bundle '{bundle}' has a reverse dependency ({dep_type}) "
                        "on '{dep}', which doesn't exist"
                    ).format(
                        item=item.id,
                        bundle=item.bundle.name,
                        dep=depending_item_id,
                        dep_type=dep_type,
                    ))
                for dependent_item in dependent_items:
                    dependent_item._deps.add(item)
                    getattr(dependent_item, '_deps_' + dep_type).add(item)


def _inject_reverse_triggers(items):
    """
    Looks for 'triggered_by' and 'precedes' attributes and turns them
    into standard triggers (defined on the opposing end).
    """
    for item in items:
        for triggering_item_selector in item.triggered_by:
            try:
                triggering_items = resolve_selector(
                    triggering_item_selector,
                    items,
                    originating_item_id=item.id,
                )
            except NoSuchItem:
                raise ItemDependencyError(_(
                    "'{item}' in bundle '{bundle}' has a reverse trigger (triggered_by) "
                    "on '{dep}', which doesn't exist"
                ).format(
                    item=item.id,
                    bundle=item.bundle.name,
                    dep=triggering_item_selector,
                ))
            for triggering_item in triggering_items:
                triggering_item.triggers.add(item.id)

        for preceded_item_selector in item.precedes:
            try:
                preceded_items = resolve_selector(
                    preceded_item_selector,
                    items,
                    originating_item_id=item.id,
                )
            except NoSuchItem:
                raise ItemDependencyError(_(
                    "'{item}' in bundle '{bundle}' has a reverse trigger (precedes) "
                    "on '{dep}', which doesn't exist"
                ).format(
                    item=item.id,
                    bundle=item.bundle.name,
                    dep=preceded_item_selector,
                ))
            for preceded_item in preceded_items:
                preceded_item.preceded_by.add(item.id)


def _inject_trigger_dependencies(items):
    """
    Injects dependencies from all triggered items to their triggering
    items.
    """
    for item in items:
        item._deps_triggers = set()

    for item in items:
        for triggered_item_selector in item.triggers:
            try:
                triggered_items = resolve_selector(
                    triggered_item_selector,
                    items,
                    originating_item_id=item.id,
                )
            except KeyError:
                raise BundleError(_(
                    "unable to find definition of '{item1}' triggered "
                    "by '{item2}' in bundle '{bundle}'"
                ).format(
                    bundle=item.bundle.name,
                    item1=triggered_item_selector,
                    item2=item.id,
                ))
            for triggered_item in triggered_items:
                if triggered_item.triggered:
                    triggered_item._deps.add(item)
                    triggered_item._deps_triggers.add(item)
                else:
                    raise BundleError(_(
                        "'{item1}' in bundle '{bundle1}' triggered "
                        "by '{item2}' in bundle '{bundle2}', "
                        "but missing 'triggered' attribute"
                    ).format(
                        item1=triggered_item.id,
                        bundle1=triggered_item.bundle.name,
                        item2=item.id,
                        bundle2=item.bundle.name,
                    ))


def _inject_preceded_by_dependencies(items):
    """
    Injects dependencies from all triggering items to their
    preceded_by items and attaches triggering items to preceding items.
    """
    for item in items:
        if item.preceded_by and item.triggered:
            raise BundleError(_(
                "triggered item '{item}' in bundle '{bundle}' must not use "
                "'preceded_by' (use chained triggers instead)".format(
                    bundle=item.bundle.name,
                    item=item.id,
                ),
            ))
        for triggered_item_selector in item.preceded_by:
            try:
                triggered_items = resolve_selector(
                    triggered_item_selector,
                    items,
                    originating_item_id=item.id,
                )
            except KeyError:
                raise BundleError(_(
                    "unable to find definition of '{item1}' preceding "
                    "'{item2}' in bundle '{bundle}'"
                ).format(
                    bundle=item.bundle.name,
                    item1=triggered_item_selector,
                    item2=item.id,
                ))
            for triggered_item in triggered_items:
                if triggered_item.triggered:
                    triggered_item._precedes_items.add(item)
                    item._deps.add(triggered_item)
                else:
                    raise BundleError(_(
                        "'{item1}' in bundle '{bundle1}' precedes "
                        "'{item2}' in bundle '{bundle2}', "
                        "but missing 'triggered' attribute"
                    ).format(
                        item1=triggered_item.id,
                        bundle1=triggered_item.bundle.name,
                        item2=item.id,
                        bundle2=item.bundle.name,
                    ))


def _inject_tag_attrs(items, bundles):
    """
    Applies the tag-level attributes from bundle.py to all matching
    items.
    """
    for bundle in bundles:
        for tag, attrs in bundle.bundle_attrs.get('tags', {}).items():
            for item in resolve_selector(f"tag:{tag}", items, originating_tag=tag):
                for attr in (
                    "after",
                    "before",
                    "needs",
                    "needed_by",
                    "precedes",
                    "preceded_by",
                    "triggers",
                    "triggered_by",
                ):
                    getattr(item, attr).update(attrs.get(attr, set()))


def _add_inherited_tags(items, bundles):
    """
    This will apply tags to items based on the tags in bundle.py.

    tags = {
        "foo": {
            "tags": {"bar"},  # will cause all items with tag:foo
                              # to also have tag:bar
        },
    }
    """
    tags_added = True
    while tags_added:
        tags_added = False
        for bundle in bundles:
            for tag, attrs in bundle.bundle_attrs.get('tags', {}).items():
                inherited_tags = attrs.get('tags', set())
                if not inherited_tags:
                    # just an optimization to avoid needlessly calling resolve_selector()
                    continue
                for item in resolve_selector(f"tag:{tag}", items):
                    len_before = len(item.tags)
                    item.tags.update(inherited_tags)
                    if len_before < len(item.tags):
                        tags_added = True


@io.job_wrapper(_("{}  processing dependencies").format(bold("{0.name}")))
def prepare_dependencies(node):
    """
    Performs all dependency preprocessing on a list of items.
    """
    for item in node.items:
        item._check_loopback_dependency()
        
    items = set(node.items)  # might be a tuple from cached_property
    _inject_canned_actions(items)
    _inject_tag_filler_items(items, node.bundles)
    _add_inherited_tags(items, node.bundles)
    _inject_tag_attrs(items, node.bundles)
    _prepare_auto_attrs(items)
    _prepare_deps(items)
    _inject_reverse_triggers(items)
    _inject_reverse_dependencies(items)
    _inject_trigger_dependencies(items)
    _inject_preceded_by_dependencies(items)
    _flatten_dependencies(items)
    _add_incoming_needs(items)

    return items


def remove_dep_from_items(items, dep):
    """
    Removes the given item id (dep) from the temporary list of
    dependencies of all items in the given list.
    """
    for item in items:
        with suppress(KeyError):
            item._deps.remove(dep)
    return items


def remove_item_dependents(items, dep_item):
    """
    Removes the items depending on the given item from the list of items.
    """
    removed_items = set()
    for item in items:
        if dep_item in item._deps_needs | item._deps_needed_by:
            removed_items.add(item)
        with suppress(KeyError):
            item._deps.remove(dep_item)

    for item in removed_items:
        items.remove(item)

    if removed_items:
        io.debug(
            "skipped these items because they depend on {item}, which was "
            "skipped previously: {skipped}".format(
                item=dep_item.id,
                skipped=", ".join([item.id for item in removed_items]),
            )
        )

    all_recursively_removed_items = set()
    for removed_item in removed_items:
        if removed_item.cascade_skip:
            items, recursively_removed_items = \
                remove_item_dependents(items, removed_item)
            all_recursively_removed_items.update(recursively_removed_items)
        else:
            items = remove_dep_from_items(items, removed_item)

    return (items, removed_items | all_recursively_removed_items)


def split_items_without_deps(items):
    """
    Takes a list of items and extracts the ones that don't have any
    dependencies. The extracted deps are returned as a list.
    """
    remaining_items = set()
    removed_items = set()
    for item in items:
        if item._deps:
            remaining_items.add(item)
        else:
            removed_items.add(item)
    return (remaining_items, removed_items)
