from .exceptions import BundleError
from .items import Item
from .items.actions import Action
from .utils import LOG
from .utils.text import mark_for_translation as _


class BundleItem(object):
    """
    Represents a dependency on all items in a certain bundle.
    """
    PARALLEL_APPLY = True

    def __init__(self, bundle):
        self.DEPENDS_STATIC = []
        self.depends = []
        self.bundle_name = bundle.name
        self.ITEM_TYPE_NAME = 'dummy'
        self.triggers = []
        self._deps = []

    def __repr__(self):
        return "<BundleItem: {}>".format(self.bundle_name)

    @property
    def id(self):
        return "bundle:{}".format(self.bundle_name)

    def apply(self, *args, **kwargs):
        return Item.STATUS_OK

    def test(self):
        pass


class DummyItem(object):
    """
    Represents a dependency on all items of a certain type.
    """
    bundle = None

    def __init__(self, item_type):
        self.DEPENDS_STATIC = []
        self.depends = []
        self.item_type = item_type
        self.ITEM_TYPE_NAME = 'dummy'
        self.triggers = []
        self._deps = []

    def __repr__(self):
        return "<DummyItem: {}>".format(self.item_type)

    @property
    def id(self):
        return "{}:".format(self.item_type)

    def apply(self, *args, **kwargs):
        return Item.STATUS_OK

    def test(self):
        pass


def find_item(item_id, items):
    """
    Returns the first item with the given ID within the given list of
    items.
    """
    try:
        item = filter(lambda item: item.id == item_id, items)[0]
    except IndexError:
        raise ValueError(_("item not found: {}").format(item_id))
    return item


def _find_items_of_type(item_type, items):
    """
    Returns a subset of items with the given type.
    """
    return filter(
        lambda item: item.id.startswith(item_type + ":"),
        items,
    )


def _flatten_dependencies(items):
    """
    This will cause all dependencies - direct AND inherited - to be
    listed in item._deps.
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
                continue

            try:
                type_name, item_name, action_name = triggered_item_id.split(":")
            except ValueError:
                continue

            target_item_id = "{}:{}".format(type_name, item_name)

            try:
                target_item = find_item(target_item_id, items)
            except ValueError:
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
    Looks for items with PARALLEL_APPLY set to False and inserts
    dependencies to force a sequential apply.
    """
    # find every item type that cannot be applied in parallel
    item_types = []
    for item in items:
        if (
            isinstance(item, DummyItem) or
            item.PARALLEL_APPLY or
            item.ITEM_TYPE_NAME in item_types
        ):
            continue
        else:
            item_types.append(item.ITEM_TYPE_NAME)

    # daisy-chain all other items of the same type (linked list style)
    # while respecting existing inter-item dependencies
    for item_type in item_types:
        type_items = _find_items_of_type(item_type, items)
        processed_items = []
        for item in type_items:
            # disregard deps to items of other types
            item.__deps = filter(
                lambda dep: dep.startswith(item_type + ":"),
                item._flattened_deps,
            )
        previous_item = None
        while len(processed_items) < len(type_items):
            # find the first item without same-type deps we haven't
            # processed yet
            item = filter(
                lambda item: not item.__deps and item not in processed_items,
                type_items,
            )[0]
            if previous_item is not None:  # unless we're at the first item
                # add dep to previous item -- unless it's already in there
                if not previous_item.id in item._deps:
                    item._deps.append(previous_item.id)
            previous_item = item
            processed_items.append(item)
            for other_item in type_items:
                try:
                    other_item.__deps.remove(item.id)
                except ValueError:
                    pass
    return items


def _inject_dummy_items(items):
    """
    Takes a list of items and adds dummy items depending on each type of
    item in the list. Returns the appended list.
    """
    # first, find all types of items and add dummy deps
    dummy_items = {}
    items = list(items)
    for item in items:
        # create dummy items that depend on each item of their type
        item_type = item.id.split(":")[0]
        if item_type not in dummy_items:
            dummy_items[item_type] = DummyItem(item_type)
        dummy_items[item_type]._deps.append(item.id)

        # create DummyItem for every type
        for dep in item._deps:
            item_type = dep.split(":")[0]
            if item_type not in dummy_items:
                dummy_items[item_type] = DummyItem(item_type)
    return list(dummy_items.values()) + items


def _inject_trigger_dependencies(items):
    """
    Injects dependencies from all triggered items to their triggering
    items.
    """
    for item in items:
        for triggered_item_id in item.triggers:
            try:
                triggered_item = find_item(triggered_item_id, items)
            except ValueError:
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


def prepare_dependencies(items):
    """
    Performs all dependency preprocessing on a list of items.
    """
    items = list(items)

    for item in items:
        item._check_bundle_collisions(items)
        item._prepare_deps(items)

    items = _inject_dummy_items(items)
    items = _inject_bundle_items(items)
    items = _inject_canned_actions(items)
    items = _inject_trigger_dependencies(items)
    items = _flatten_dependencies(items)
    items = _inject_concurrency_blockers(items)
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


def remove_item_dependents(items, dep):
    """
    Removes the items depending on the given id from the list of items.
    """
    removed_items = []
    for item in items:
        # remove failed item from static and concurrency blocker deps
        try:
            item._deps.remove(dep)
        except ValueError:
            pass
        # only cascade item abort if it was an explicit dep
        if dep in item.depends:
            items.remove(item)
            removed_items.append(item)

    if removed_items:
        LOG.debug(
            "skipped these items because they depend on {item}, which was "
            "skipped previously: {skipped}".format(
                item=dep,
                skipped=", ".join([item.id for item in removed_items]),
            )
        )

    all_recursively_removed_items = []
    for removed_item in removed_items:
        items, recursively_removed_items = \
            remove_item_dependents(items, removed_item.id)
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
