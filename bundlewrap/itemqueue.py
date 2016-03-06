from .deps import (
    DummyItem,
    find_item,
    prepare_dependencies,
    remove_item_dependents,
    remove_dep_from_items,
    split_items_without_deps,
)
from .exceptions import NoSuchItem
from .utils.text import mark_for_translation as _
from .utils.ui import io


class BaseQueue(object):
    def __init__(self, items):
        self.items_with_deps = prepare_dependencies(items)
        self.items_without_deps = []
        self._split()
        self.pending_items = []

    def _split(self):
        self.items_with_deps, self.items_without_deps = \
            split_items_without_deps(self.all_items)

    @property
    def all_items(self):
        return self.items_with_deps + self.items_without_deps


class ItemQueue(BaseQueue):
    def item_failed(self, item):
        """
        Called when an item could not be fixed. Yields all items that
        have been skipped as a result by cascading.
        """
        for skipped_item in self.item_skipped(item, _skipped=False):
            yield skipped_item

    def item_fixed(self, item):
        """
        Called when an item has successfully been fixed.
        """
        self.item_ok(item)
        self._fire_triggers_for_item(item)

    def item_ok(self, item):
        """
        Called when an item didn't need to be fixed.
        """
        self.pending_items.remove(item)
        # if an item is applied successfully, all dependencies on it can
        # be removed from the remaining items
        self.items_with_deps = remove_dep_from_items(
            self.items_with_deps,
            item.id,
        )
        self._split()

    def item_skipped(self, item, _skipped=True):
        """
        Called when an item has been skipped. Yields all items that have
        been skipped as a result by cascading.
        """
        self.pending_items.remove(item)
        if item.cascade_skip:
            # if an item fails or is skipped, all items that depend on
            # it shall be removed from the queue
            self.items_with_deps, skipped_items = remove_item_dependents(
                self.items_with_deps,
                item,
                skipped=_skipped,
            )
            # since we removed them from further processing, we
            # fake the status of the removed items so they still
            # show up in the result statistics
            for skipped_item in skipped_items:
                if not isinstance(skipped_item, DummyItem):
                    yield skipped_item
        else:
            self.items_with_deps = remove_dep_from_items(
                self.items_with_deps,
                item.id,
            )
        self._split()

    def pop(self, interactive=False):
        """
        Gets the next item available for processing and moves it into
        self.pending_items. Will raise IndexError if no item is
        available. Otherwise, it will return the item and a list of
        items that have been skipped while looking for the item.
        """
        skipped_items = []

        if not self.items_without_deps:
            raise IndexError

        while self.items_without_deps:
            item = self.items_without_deps.pop()

            if item._precedes_items:
                if item._precedes_incorrect_item(interactive=interactive):
                    item.has_been_triggered = True
                else:
                    # we do not have to cascade here at all because
                    # all chained preceding items will be skipped by
                    # this same mechanism
                    io.debug(
                        _("skipping {node}:{bundle}:{item} because its precede trigger "
                          "did not fire").format(
                            bundle=item.bundle.name,
                            item=item.id,
                            node=item.node.name,
                        ),
                    )
                    self.items_with_deps = remove_dep_from_items(self.items_with_deps, item.id)
                    self._split()
                    skipped_items.append(item)
                    item = None
                    continue
            break
        assert item is not None
        self.pending_items.append(item)
        return (item, skipped_items)

    def _fire_triggers_for_item(self, item):
        for triggered_item_id in item.triggers:
            try:
                triggered_item = find_item(
                    triggered_item_id,
                    self.all_items,
                )
                triggered_item.has_been_triggered = True
            except NoSuchItem:
                io.debug(_(
                    "{item} tried to trigger {triggered_item}, "
                    "but it wasn't available. It must have been skipped previously."
                ).format(
                    item=item.id,
                    triggered_item=triggered_item_id,
                ))


class ItemTestQueue(BaseQueue):
    """
    A simpler variation of ItemQueue that is used by `bw test` to check
    for circular dependencies.
    """
    def pop(self):
        item = self.items_without_deps.pop()
        self.items_with_deps = remove_dep_from_items(self.items_with_deps, item.id)
        self._split()
        return item
