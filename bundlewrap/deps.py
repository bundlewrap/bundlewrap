# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from .exceptions import BundleError, NoSuchItem
from .items import Item
from .items.actions import Action
from .utils.text import mark_for_translation as _
from .utils.ui import io


class DummyItem(object):
    bundle = None
    triggered = False

    def __init__(self, *args, **kwargs):
        self.needed_by = []
        self.needs = []
        self.preceded_by = []
        self.precedes = []
        self.tags = []
        self.triggered_by = []
        self.triggers = []
        self._deps = []
        self._precedes_items = []

    def __lt__(self, other):
        return self.id < other.id

    def apply(self, *args, **kwargs):
        return (Item.STATUS_OK, [])

    def test(self):
        pass


class BundleItem(DummyItem):
    """
    Represents a dependency on all items in a certain bundle.
    """
    ITEM_TYPE_NAME = 'bundle'

    def __init__(self, bundle):
        self.bundle = bundle
        super(BundleItem, self).__init__()

    def __repr__(self):
        return "<BundleItem: {}>".format(self.bundle.name)

    @property
    def id(self):
        return "bundle:{}".format(self.bundle.name)


class TagItem(DummyItem):
    """
    This item depends on all items with the given tag.
    """
    ITEM_TYPE_NAME = 'tag'

    def __init__(self, tag_name):
        self.tag_name = tag_name
        super(TagItem, self).__init__()

    def __repr__(self):
        return "<TagItem: {}>".format(self.tag_name)

    @property
    def id(self):
        return "tag:{}".format(self.tag_name)


class TypeItem(DummyItem):
    """
    Represents a dependency on all items of a certain type.
    """
    ITEM_TYPE_NAME = 'type'

    def __init__(self, item_type):
        self.item_type = item_type
        super(TypeItem, self).__init__()

    def __repr__(self):
        return "<TypeItem: {}>".format(self.item_type)

    @property
    def id(self):
        return "{}:".format(self.item_type)


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


def _find_items_of_types(item_types, items, include_dummy=False):
    """
    Returns a subset of items with any of the given types.
    """
    return list(filter(
        lambda item:
            item.id.split(":", 1)[0] in item_types and (
                include_dummy or not isinstance(item, DummyItem)
            ),
        items,
    ))


def _flatten_dependencies(items):
    """
    This will cause all dependencies - direct AND inherited - to be
    listed in item._flattened_deps.
    """
    for item in items:
        item._flattened_deps = list(set(
            item._deps + _get_deps_for_item(item, items)
        ))
    return items


def _get_deps_for_item(item, items, deps_found=None):
    """
    Recursively retrieves and returns a list of all inherited
    dependencies of the given item.

    Note: This can handle loops, but won't detect them.
    """
    if deps_found is None:
        deps_found = []
    deps = []
    for dep in item._deps:
        if dep not in deps_found:
            deps.append(dep)
            deps_found.append(dep)
            deps += _get_deps_for_item(
                find_item(dep, items),
                items,
                deps_found,
            )
    return deps


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


def _inject_bundle_items(items):
    """
    Adds virtual items that depend on every item in a bundle.
    """
    bundle_items = {}
    for item in items:
        if item.bundle is None:
            continue
        if item.bundle.name not in bundle_items:
            bundle_items[item.bundle.name] = BundleItem(item.bundle)
        bundle_items[item.bundle.name]._deps.append(item.id)
    return list(bundle_items.values()) + items


def _inject_canned_actions(items):
    """
    Looks for canned actions like "svc_upstart:mysql:reload" in item
    triggers and adds them to the list of items.
    """
    added_actions = {}
    for item in items:
        for triggered_item_id in item.triggers:
            if triggered_item_id in added_actions:
                # action has already been triggered
                continue

            try:
                type_name, item_name, action_name = triggered_item_id.split(":")
            except ValueError:
                # not a canned action
                continue

            target_item_id = "{}:{}".format(type_name, item_name)

            try:
                target_item = find_item(target_item_id, items)
            except NoSuchItem:
                raise BundleError(_(
                    "{item} in bundle '{bundle}' triggers unknown item '{target_item}'"
                ).format(
                    bundle=item.bundle.name,
                    item=item.id,
                    target_item=target_item_id,
                ))

            try:
                action_attrs = target_item.get_canned_actions()[action_name]
            except KeyError:
                raise BundleError(_(
                    "{item} in bundle '{bundle}' triggers unknown "
                    "canned action '{action}' on {target_item}"
                ).format(
                    action=action_name,
                    bundle=item.bundle.name,
                    item=item.id,
                    target_item=target_item_id,
                ))

            action_attrs.update({'triggered': True})
            action = Action(
                item.bundle,
                triggered_item_id,
                action_attrs,
                skip_name_validation=True,
            )
            action._prepare_deps(items)
            added_actions[triggered_item_id] = action

    return items + list(added_actions.values())


def _inject_concurrency_blockers(items):
    """
    Looks for items with BLOCK_CONCURRENT set to True and inserts
    dependencies to force a sequential apply.
    """
    # find every item type that cannot be applied in parallel
    item_types = set()
    for item in items:
        item._concurrency_deps = []
        if (
            not isinstance(item, DummyItem) and
            item.BLOCK_CONCURRENT
        ):
            item_types.add(item.__class__)

    # daisy-chain all items of the blocking type and all items of the
    # blocked types while respecting existing dependencies between them
    for item_type in item_types:
        blocked_types = item_type.BLOCK_CONCURRENT + [item_type.ITEM_TYPE_NAME]
        type_items = _find_items_of_types(
            blocked_types,
            items,
        )
        processed_items = []
        for item in type_items:
            # disregard deps to items of other types
            item.__deps = list(filter(
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
                if previous_item.id not in item._deps:
                    item._deps.append(previous_item.id)
                    item._concurrency_deps.append(previous_item.id)
                    item._flattened_deps.append(previous_item.id)
            previous_item = item
            processed_items.append(item)
            for other_item in type_items:
                try:
                    other_item.__deps.remove(item.id)
                except ValueError:
                    pass
    return items


def _inject_tag_items(items):
    """
    Takes a list of items and adds tag items depending on each type of
    item in the list. Returns the appended list.
    """
    tag_items = {}
    items = list(items)
    for item in items:
        for tag in item.tags:
            if tag not in tag_items:
                tag_items[tag] = TagItem(tag)
            tag_items[tag]._deps.append(item.id)

    return list(tag_items.values()) + items


def _inject_type_items(items):
    """
    Takes a list of items and adds dummy items depending on each type of
    item in the list. Returns the appended list.
    """
    # first, find all types of items and add dummy deps
    type_items = {}
    items = list(items)
    for item in items:
        # create dummy items that depend on each item of their type
        item_type = item.id.split(":")[0]
        if item_type not in type_items:
            type_items[item_type] = TypeItem(item_type)
        type_items[item_type]._deps.append(item.id)

        # create DummyItem for every type
        for dep in item._deps:
            item_type = dep.split(":")[0]
            if item_type not in type_items:
                type_items[item_type] = TypeItem(item_type)
    return list(type_items.values()) + items


def _inject_reverse_dependencies(items):
    """
    Looks for 'needed_by' deps and creates standard dependencies
    accordingly.
    """
    def add_dep(item, dep):
        if dep not in item._deps:
            item._deps.append(dep)
            item._reverse_deps.append(dep)

    for item in items:
        item._reverse_deps = []

    for item in items:
        for depending_item_id in item.needed_by:
            # bundle items
            if depending_item_id.startswith("bundle:"):
                depending_bundle_name = depending_item_id.split(":")[1]
                for depending_item in items:
                    if depending_item.bundle.name == depending_bundle_name:
                        add_dep(depending_item, item.id)

            # tag items
            if depending_item_id.startswith("tag:"):
                tag_name = depending_item_id.split(":")[1]
                for depending_item in items:
                    if tag_name in depending_item.tags:
                        add_dep(depending_item, item.id)

            # type items
            if depending_item_id.endswith(":"):
                target_type = depending_item_id[:-1]
                for depending_item in _find_items_of_types([target_type], items):
                    add_dep(depending_item, item.id)

            # single items
            else:
                depending_item = find_item(depending_item_id, items)
                add_dep(depending_item, item.id)
    return items


def _inject_reverse_triggers(items):
    """
    Looks for 'triggered_by' and 'precedes' attributes and turns them
    into standard triggers (defined on the opposing end).
    """
    for item in items:
        for triggering_item_id in item.triggered_by:
            triggering_item = find_item(triggering_item_id, items)
            triggering_item.triggers.append(item.id)
        for preceded_item_id in item.precedes:
            preceded_item = find_item(preceded_item_id, items)
            preceded_item.preceded_by.append(item.id)
    return items


def _inject_trigger_dependencies(items):
    """
    Injects dependencies from all triggered items to their triggering
    items.
    """
    for item in items:
        for triggered_item_id in item.triggers:
            try:
                triggered_item = find_item(triggered_item_id, items)
            except NoSuchItem:
                raise BundleError(_(
                    "unable to find definition of '{item1}' triggered "
                    "by '{item2}' in bundle '{bundle}'"
                ).format(
                    bundle=item.bundle.name,
                    item1=triggered_item_id,
                    item2=item.id,
                ))
            if not triggered_item.triggered:
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
            triggered_item._deps.append(item.id)
    return items


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
        for triggered_item_id in item.preceded_by:
            try:
                triggered_item = find_item(triggered_item_id, items)
            except NoSuchItem:
                raise BundleError(_(
                    "unable to find definition of '{item1}' preceding "
                    "'{item2}' in bundle '{bundle}'"
                ).format(
                    bundle=item.bundle.name,
                    item1=triggered_item_id,
                    item2=item.id,
                ))
            if not triggered_item.triggered:
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
            triggered_item._precedes_items.append(item)
            item._deps.append(triggered_item.id)
    return items


def prepare_dependencies(items):
    """
    Performs all dependency preprocessing on a list of items.
    """
    items = list(items)

    for item in items:
        item._check_bundle_collisions(items)
        item._prepare_deps(items)

    items = _inject_bundle_items(items)
    items = _inject_tag_items(items)
    items = _inject_type_items(items)
    items = _inject_canned_actions(items)
    items = _inject_reverse_triggers(items)
    items = _inject_reverse_dependencies(items)
    items = _inject_trigger_dependencies(items)
    items = _inject_preceded_by_dependencies(items)
    items = _flatten_dependencies(items)
    items = _inject_concurrency_blockers(items)

    for item in items:
        if not isinstance(item, DummyItem):
            item._check_redundant_dependencies()

    return items


def remove_dep_from_items(items, dep):
    """
    Removes the given item id (dep) from the temporary list of
    dependencies of all items in the given list.
    """
    for item in items:
        try:
            item._deps.remove(dep)
        except ValueError:
            pass
    return items


def remove_item_dependents(items, dep_item, skipped=False):
    """
    Removes the items depending on the given item from the list of items.
    """
    removed_items = []
    for item in items:
        if dep_item.id in item._deps:
            if _has_trigger_path(items, dep_item, item.id):
                # triggered items cannot be removed here since they
                # may yet be triggered by another item and will be
                # skipped anyway if they aren't
                item._deps.remove(dep_item.id)
            elif skipped and isinstance(item, DummyItem) and \
                    dep_item.triggered and not dep_item.has_been_triggered:
                # don't skip dummy items because of untriggered members
                # see issue #151; separate elif for clarity
                item._deps.remove(dep_item.id)
            else:
                removed_items.append(item)

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

    all_recursively_removed_items = []
    for removed_item in removed_items:
        items, recursively_removed_items = \
            remove_item_dependents(items, removed_item, skipped=skipped)
        all_recursively_removed_items += recursively_removed_items

    return (items, removed_items + all_recursively_removed_items)


def split_items_without_deps(items):
    """
    Takes a list of items and extracts the ones that don't have any
    dependencies. The extracted deps are returned as a list.
    """
    items = list(items)  # make sure we're not returning a generator
    removed_items = []
    for item in items:
        if not item._deps:
            removed_items.append(item)
    for item in removed_items:
        items.remove(item)
    return (items, removed_items)
