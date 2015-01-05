from unittest import TestCase

from .node_tests import get_mock_item

from bundlewrap import itemqueue


class ItemQueueFireTriggersTest(TestCase):
    """
    Tests bundlewrap.itemqueue.ItemQueue._fire_triggers_for_item().
    """
    def test_item_previously_skipped(self):
        item1 = get_mock_item("type1", "name1", [], [])
        item1.cascade_skip = True
        item2 = get_mock_item("type1", "name2", [], [])
        item2.triggers = ["type1:name3"]
        item3 = get_mock_item("type1", "name3", [], ["type1:name1"])
        item3.triggered = True
        iq = itemqueue.ItemQueue([item1, item2, item3])
        popped_item = iq.pop()
        self.assertEqual(popped_item, item2)
        popped_item = iq.pop()
        self.assertEqual(popped_item, item1)
        # skipping item1 will result in item3 being skipped
        self.assertEqual(list(iq.item_skipped(item1)), [item3])
        # item2 triggering item3 fails silently
        iq.item_fixed(item2)


class ItemQueueItemFailedTest(TestCase):
    """
    Tests bundlewrap.itemqueue.ItemQueue.item_failed().
    """
    def test_item_failed(self):
        item1 = get_mock_item("type1", "name1", [], [])
        item2 = get_mock_item("type1", "name2", [], ["type1:name1"])
        iq = itemqueue.ItemQueue([item1, item2])
        popped_item = iq.pop()
        self.assertEqual(popped_item, item1)
        self.assertEqual(
            list(iq.item_failed(popped_item)),
            [item2],
        )
        with self.assertRaises(IndexError):
            iq.pop()


class ItemQueueItemFixedTest(TestCase):
    """
    Tests bundlewrap.itemqueue.ItemQueue.item_fixed().
    """
    def test_item_triggered(self):
        item1 = get_mock_item("type1", "name1", [], [])
        item1.triggers = ["type1:name2"]
        item2 = get_mock_item("type1", "name2", [], [])
        item2.triggered = True
        iq = itemqueue.ItemQueue([item1, item2])
        popped_item = iq.pop()
        self.assertEqual(popped_item, item1)
        iq.item_fixed(popped_item)
        popped_item = iq.pop()
        self.assertEqual(popped_item, item2)
        self.assertTrue(popped_item.has_been_triggered)


class ItemQueueItemOKTest(TestCase):
    """
    Tests bundlewrap.itemqueue.ItemQueue.item_ok().
    """
    def test_single_ok(self):
        item = get_mock_item("type1", "name1", [], [])
        iq = itemqueue.ItemQueue([item])
        pending_item = iq.pop()
        iq.item_ok(pending_item)
        self.assertEqual(iq.items_with_deps, [])
        self.assertEqual(iq.pending_items, [])
        # just the bundle and type dummy items remain
        self.assertEqual(len(iq.items_without_deps), 2)

    def test_dependency(self):
        item1 = get_mock_item("type1", "name1", [], [])
        item2 = get_mock_item("type1", "name2", [], ["type1:name1"])
        iq = itemqueue.ItemQueue([item1, item2])
        popped_item = iq.pop()
        self.assertEqual(popped_item, item1)
        iq.item_ok(popped_item)
        popped_item = iq.pop()
        self.assertEqual(popped_item, item2)

    def test_item_not_triggered(self):
        item1 = get_mock_item("type1", "name1", [], [])
        item1.triggers = ["type1:name2"]
        item2 = get_mock_item("type1", "name2", [], [])
        item2.triggered = True
        iq = itemqueue.ItemQueue([item1, item2])
        popped_item = iq.pop()
        self.assertEqual(popped_item, item1)
        iq.item_ok(popped_item)
        popped_item = iq.pop()
        self.assertEqual(popped_item, item2)
        self.assertFalse(popped_item.has_been_triggered)


class ItemQueueItemSkippedTest(TestCase):
    """
    Tests bundlewrap.itemqueue.ItemQueue.item_skipped().
    """
    def test_item_skipped(self):
        item1 = get_mock_item("type1", "name1", [], [])
        item2 = get_mock_item("type1", "name2", [], ["type1:name1"])
        iq = itemqueue.ItemQueue([item1, item2])
        popped_item = iq.pop()
        self.assertEqual(popped_item, item1)
        self.assertEqual(
            list(iq.item_skipped(popped_item)),
            [item2],
        )
        with self.assertRaises(IndexError):
            iq.pop()


class ItemQueuePopTest(TestCase):
    """
    Tests bundlewrap.itemqueue.ItemQueue.pop().
    """
    def test_pop_empty(self):
        iq = itemqueue.ItemQueue([])
        with self.assertRaises(IndexError):
            iq.pop()

    def test_pop_single(self):
        item = get_mock_item("type1", "name1", [], [])
        iq = itemqueue.ItemQueue([item])
        self.assertEqual(iq.pop(), item)
        with self.assertRaises(IndexError):
            iq.pop()
        self.assertEqual(iq.pending_items, [item])
