from collections import defaultdict

from .deps import (
    find_item,
    prepare_dependencies,
    remove_item_dependents,
    remove_dep_from_items,
    split_items_without_deps,
)
from .exceptions import NoSuchItem
from .utils.text import mark_for_translation as _
from .utils.ui import io


class BaseQueue:
    def __init__(self, node):
        self.items_with_deps = prepare_dependencies(node)
        self.items_without_deps = set()
        self._split()
        self.pending_items = set()

    def _split(self):
        self.items_with_deps, self.items_without_deps = \
            split_items_without_deps(self.all_items)

    @property
    def all_items(self):
        return self.items_with_deps | self.items_without_deps


class ItemQueue(BaseQueue):
    def __init__(self, node):
        super().__init__(node)

        # Optional sanity check.
        self.item_types_with_blockers = set()

    def item_failed(self, item):
        """
        Called when an item could not be fixed. Yields all items that
        have been skipped as a result by cascading.
        """
        for skipped_item in self.item_skipped(item):
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
            item,
        )
        self._split()

    def item_skipped(self, item):
        """
        Called when an item has been skipped. Yields all items that have
        been skipped as a result by cascading.
        """
        self.pending_items.remove(item)
        if item.cascade_skip:  # TODO 5.0 always do this when removing cascade_skip
            # if an item fails or is skipped, all items that depend on
            # it shall be removed from the queue
            self.items_with_deps, skipped_items = remove_item_dependents(
                self.items_with_deps,
                item,
            )
            for skipped_item in skipped_items:
                yield skipped_item
        else:
            self.items_with_deps = remove_dep_from_items(
                self.items_with_deps,
                item,
            )
        self._split()

    def items_without_deps_runnable(self):
        runnable_items = set()
        running_item_types = set([i.ITEM_TYPE_NAME for i in self.pending_items])

        for item in self.items_without_deps:
            add_this_item = True
            for item_blocked_for in item.block_concurrent(item.node.os, item.node.os_version):
                # Optional sanity check.
                #
                # Keep track of item types that have blockers. We can
                # later use this to do a sanity check: Was there a bug
                # and did we accidentally run blocked items after all?
                #
                # Note that this does NOT catch all cases that are
                # theoretically possible. It only catches things like
                # pkg_apt where only one item of that exact type can be
                # running.
                self.item_types_with_blockers.add(item.ITEM_TYPE_NAME)

                if item_blocked_for in running_item_types:
                    add_this_item = False
                    break

            if add_this_item:
                runnable_items.add(item)

        return runnable_items

    def pop(self):
        """
        Gets the next item available for processing and moves it into
        self.pending_items. Will raise KeyError if no item is
        available.
        """
        runnable_items = self.items_without_deps_runnable()

        if not runnable_items:
            raise KeyError

        item = runnable_items.pop()
        self.items_without_deps.remove(item)

        self.pending_items.add(item)

        # Optional sanity check.
        item_types_running = defaultdict(int)
        for i in self.pending_items:
            item_types_running[i.ITEM_TYPE_NAME] += 1
        for it in self.item_types_with_blockers:
            if item_types_running[it] > 1:
                raise Exception(f'BUG! More than one {it} running!')

        return item

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
        self.items_with_deps = remove_dep_from_items(self.items_with_deps, item)
        self._split()
        return item
