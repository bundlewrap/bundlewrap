from contextlib import suppress

from .exceptions import BundleError, ItemDependencyError, NoSuchItem
from .items import Item
from .items.actions import Action
from .utils.text import bold, mark_for_translation as _
from .utils.ui import io


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

    for item in items:
        item._incoming_deps = set()
        for other_item in items:
            if item.id in other_item._flattened_deps:
                item._incoming_deps.add(other_item)


def _flatten_deps_for_item(item, items):
    """
    Recursively retrieves and returns a list of all inherited
    dependencies of the given item.

    This can handle loops, but will ignore them.
    """
    item._flattened_deps = {item.id for item in item._deps}

    for dep_item in item._deps:
        # Don't recurse if we have already resolved nested
        # dependencies for this item. Also serves as a guard
        # against infinite recursion when there are loops.
        if not hasattr(dep_item, '_flattened_deps'):
            _flatten_deps_for_item(dep_item, items)

        item._flattened_deps.update(dep_item._flattened_deps)


def _has_trigger_path(items, item, target_item_id):
    """
    Returns True if the given item directly or indirectly (trough
    other items) triggers the item with the given target item id.
    """
    if target_item_id in item.triggers:
        return True
    for triggered_id in item.triggers:
        try:
            triggered_item = find_item(triggered_id, items)
        except NoSuchItem:
            # the triggered item may already have been skipped by
            # `bw apply -s`
            continue
        if _has_trigger_path(items, triggered_item, target_item_id):
            return True
    return False


def _prepare_deps(items):
    for item in items:
        item._deps = set()
        for dep in list(item.needs) + list(item.get_auto_deps(items)):
            try:
                item._deps.update(resolve_selector(dep, items, originating_item_id=item.id))
            except NoSuchItem:
                raise ItemDependencyError(_(
                    "'{item}' in bundle '{bundle}' has a dependency (needs) "
                    "on '{dep}', which doesn't exist"
                ).format(
                    item=item.id,
                    bundle=item.bundle.name,
                    dep=dep,
                ))


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


def _inject_concurrency_blockers(items, node_os, node_os_version):
    """
    Looks for items with BLOCK_CONCURRENT set and inserts daisy-chain
    dependencies to force a sequential apply.
    """
    # find every item type that cannot be applied in parallel
    item_types = set()
    for item in items:
        item._concurrency_deps = set()  # used for DOT (graphviz) output only
        if item.block_concurrent(node_os, node_os_version):
            item_types.add(item.__class__)

    # Now that we have collected all relevant types,
    # we must group them together when they overlap. E.g.:
    #
    #     Type1.block_concurrent(...) == ["type1", "type2"]
    #     Type2.block_concurrent(...) == ["type2", "type3"]
    #     Type4.block_concurrent(...) == ["type4"]
    #
    # becomes
    #
    #     ["type1", "type2", "type3"]
    #     ["type4"]
    #
    # because the first two types overlap in blocking type2. This is
    # necessary because existing dependencies from type3 to type1 need
    # to be taken into account when generating the daisy-chains
    # connecting the three types. If we processed blockers for Type1 and
    # Type2 independently, we might end up with two very different
    # chains for Type2, which may cause circular dependencies.

    chain_groups = []
    for item_type in item_types:
        block_concurrent = {item_type.ITEM_TYPE_NAME}
        block_concurrent.update(item_type.block_concurrent(node_os, node_os_version))
        for blocked_types in chain_groups:
            for blocked_type in block_concurrent:
                if blocked_type in blocked_types:
                    blocked_types.update(block_concurrent)
                    break
        else:
            chain_groups.append(block_concurrent)

    # daisy-chain all items of the chain group while respecting existing
    # dependencies between them
    for blocked_types in chain_groups:
        blocked_types = set(blocked_types)
        type_items = set(filter(
            lambda item: item.ITEM_TYPE_NAME in blocked_types,
            items,
        ))
        processed_items = set()
        for item in type_items:
            # disregard deps to items of other types
            item.__deps = set(filter(
                lambda dep: dep.split(":", 1)[0] in blocked_types,
                item._flattened_deps,
            ))
        previous_item = None
        while len(processed_items) < len(type_items):
            # find the first item without same-type deps we haven't
            # processed yet
            try:
                item = list(filter(
                    lambda item: not item.__deps and item not in processed_items,
                    type_items,
                ))[0]
            except IndexError:
                # this can happen if the flattened deps of all items of
                # this type already contain a dependency on another
                # item of this type
                break
            if previous_item is not None:  # unless we're at the first item
                # add dep to previous item -- unless it's already in there
                if previous_item not in item._deps:
                    item._deps.add(previous_item)
                    item._concurrency_deps.add(previous_item.id)
                    item._flattened_deps.add(previous_item.id)
            previous_item = item
            processed_items.add(item)
            # Now remove all deps on the processed item. This frees up
            # items depending *only* on the processed item to be
            # eligible for the next iteration of this loop.
            for other_item in type_items:
                with suppress(KeyError):
                    other_item.__deps.remove(item.id)


def _inject_reverse_dependencies(items):
    """
    Looks for 'needed_by' deps and creates standard dependencies
    accordingly.
    """
    def add_dep(item, dep):
        if dep not in item._deps:
            item._deps.add(dep)
            item._reverse_deps.add(dep)

    for item in items:
        item._reverse_deps = set()

    for item in items:
        for depending_item_id in item.needed_by:
            try:
                dependent_items = resolve_selector(
                    depending_item_id,
                    items,
                    originating_item_id=item.id,
                )
            except NoSuchItem:
                raise ItemDependencyError(_(
                    "'{item}' in bundle '{bundle}' has a reverse dependency (needed_by) "
                    "on '{dep}', which doesn't exist"
                ).format(
                    item=item.id,
                    bundle=item.bundle.name,
                    dep=depending_item_id,
                ))
            for dependent_item in dependent_items:
                add_dep(dependent_item, item)


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
        item._check_bundle_collisions(node.items)
        item._check_loopback_dependency()
        
    items = set(node.items)  # might be a tuple from cached_property
    _inject_canned_actions(items)
    _inject_tag_filler_items(items, node.bundles)
    _add_inherited_tags(items, node.bundles)
    _inject_tag_attrs(items, node.bundles)
    _prepare_deps(items)
    _inject_reverse_triggers(items)
    _inject_reverse_dependencies(items)
    _inject_trigger_dependencies(items)
    _inject_preceded_by_dependencies(items)
    _flatten_dependencies(items)
    _inject_concurrency_blockers(items, node.os, node.os_version)

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
        if dep_item in item._deps:
            if _has_trigger_path(items, dep_item, item.id):
                # triggered items cannot be removed here since they
                # may yet be triggered by another item and will be
                # skipped anyway if they aren't
                item._deps.remove(dep_item)
            elif dep_item.id in item._concurrency_deps:
                # don't skip items just because of concurrency deps
                # separate elif for clarity
                item._deps.remove(dep_item)
            else:
                removed_items.add(item)

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
