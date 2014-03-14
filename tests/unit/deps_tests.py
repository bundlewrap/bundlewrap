from unittest import TestCase

from mock import MagicMock

from blockwart import deps
from blockwart.exceptions import BundleError
from blockwart.items import Item


class MockItem(Item):
    BUNDLE_ATTRIBUTE_NAME = "mock"
    ITEM_TYPE_NAME = "mock"
    DEPENDS_STATIC = []

    def get_canned_actions(self):
        return {
            'action1': {
                'command': "true",
            },
        }


class FlattenDependenciesTest(TestCase):
    """
    Tests blockwart.deps._flatten_dependencies.
    """
    def test_flatten(self):
        class FakeItem(object):
            pass

        def make_item(item_id):
            item = FakeItem()
            item._deps = []
            item.id = item_id
            return item

        item1 = make_item("type1:name1")
        item2 = make_item("type1:name2")
        item3 = make_item("type2:name1")
        item3._deps = ["type1:"]
        item4 = make_item("type3:name1")
        item4._deps = ["type2:name1"]
        item5 = make_item("type1:")
        item5._deps = ["type1:name1", "type1:name2"]
        items = [item1, item2, item3, item4, item5]

        items = deps._flatten_dependencies(items)

        deps_should = {
            item1: [],
            item2: [],
            item3: ["type1:", "type1:name1", "type1:name2"],
            item4: ["type1:", "type1:name1", "type1:name2", "type2:name1"],
            item5: ["type1:name1", "type1:name2"],
        }

        for item in items:
            self.assertEqual(set(item._flattened_deps), set(deps_should[item]))


class InjectCannedActionsTest(TestCase):
    """
    Tests blockwart.deps._inject_canned_actions.
    """
    def test_injection_ok(self):
        bundle = MagicMock()
        triggering_item1 = MockItem(
            bundle,
            "triggering1",
            {'triggers': ["mock:triggered:action1"]},
        )
        triggering_item2 = MockItem(
            bundle,
            "triggering2",
            {'triggers': ["mock:triggered", "mock:triggered:action1"]},
        )
        triggered_item = MockItem(bundle, "triggered", {})
        items = deps._inject_canned_actions([
            triggering_item1,
            triggering_item2,
            triggered_item,
        ])
        action = items[3]
        self.assertEqual(action.ITEM_TYPE_NAME, 'action')
        self.assertEqual(len(items), 4)

    def test_unknown_target(self):
        bundle = MagicMock()
        triggering_item = MockItem(
            bundle,
            "triggering",
            {'triggers': ["mock:triggered:action1"]},
        )
        not_triggered_item = MockItem(bundle, "not_triggered", {})
        with self.assertRaises(BundleError):
            deps._inject_canned_actions([triggering_item, not_triggered_item])

    def test_unknown_action(self):
        bundle = MagicMock()
        triggering_item = MockItem(
            bundle,
            "triggering",
            {'triggers': ["mock:triggered:action2"]},
        )
        triggered_item = MockItem(bundle, "triggered", {})
        with self.assertRaises(BundleError):
            deps._inject_canned_actions([triggering_item, triggered_item])


class InjectDummyItemsTest(TestCase):
    """
    Tests blockwart.deps._inject_dummy_items.
    """
    def test_item_injection(self):
        class FakeItem(object):
            pass

        def make_item(item_id):
            item = FakeItem()
            item._deps = []
            item.DEPENDS_STATIC = []
            item.depends = []
            item.id = item_id
            return item

        item1 = make_item("type1:name1")
        item2 = make_item("type1:name2")
        item3 = make_item("type2:name1")
        item4 = make_item("type3:name1")
        items = [item1, item2, item3, item4]

        injected = deps._inject_dummy_items(items)

        dummy_counter = 0
        for item in injected:
            if isinstance(item, deps.DummyItem):
                self.assertTrue(len(item._deps) > 0)
                dummy_counter += 1
                for dep in item._deps:
                    self.assertTrue(dep.startswith(item.id))
        self.assertEqual(len(injected), 7)
        self.assertEqual(dummy_counter, 3)


class InjectConcurrencyBlockersTest(TestCase):
    """
    Tests blockwart.deps._inject_concurrency_blockers.
    """
    def test_blockers(self):
        class FakeItem(object):
            pass

        def make_item(item_id, parallel_apply):
            item = FakeItem()
            item._deps = []
            item._flattened_deps = []
            item.ITEM_TYPE_NAME = item_id.split(":")[0]
            item.PARALLEL_APPLY = parallel_apply
            item.id = item_id
            return item

        item11 = make_item("type1:name1", True)
        item12 = make_item("type1:name2", True)
        item21 = make_item("type2:name1", False)
        item22 = make_item("type2:name2", False)
        item23 = make_item("type2:name3", False)
        item31 = make_item("type3:name1", False)
        item32 = make_item("type3:name2", False)

        items = [item11, item32, item22, item12, item21, item23, item31]
        injected = deps._inject_concurrency_blockers(items)

        deps_should = {
            item11: [],
            item32: [],
            item22: [],
            item12: [],
            item21: ["type2:name2"],
            item23: ["type2:name1"],
            item31: ["type3:name2"],
        }

        self.assertEqual(len(injected), len(items))

        for item in injected:
            self.assertEqual(item._deps, deps_should[item])

    def test_noop(self):
        class FakeItem(object):
            pass

        def make_item(item_id):
            item = FakeItem()
            item._deps = []
            item.ITEM_TYPE_NAME = item_id.split(":")[0]
            item.PARALLEL_APPLY = True
            item.id = item_id
            return item

        item11 = make_item("type1:name1")
        item12 = make_item("type1:name2")
        item21 = make_item("type2:name1")
        item22 = make_item("type2:name2")
        item23 = make_item("type2:name3")
        item31 = make_item("type3:name1")
        item32 = make_item("type3:name2")

        items = [item11, item32, item22, item12, item21, item23, item31]
        injected = deps._inject_concurrency_blockers(items)

        deps_should = {
            item11: [],
            item32: [],
            item22: [],
            item12: [],
            item21: [],
            item23: [],
            item31: [],
        }

        self.assertEqual(len(injected), len(items))

        for item in injected:
            self.assertEqual(item._deps, deps_should[item])


class ItemSplitWithoutDepTest(TestCase):
    """
    Tests blockwart.deps.split_items_without_deps.
    """
    def test_all_deps(self):
        class FakeItem(object):
            pass
        item1 = FakeItem()
        item1._deps = ["type1:name1"]
        item2 = FakeItem()
        item2._deps = ["type1:", "type2:name2"]
        item3 = FakeItem()
        item3._deps = ["type2:"]
        items = [item1, item2, item3]
        items, removed_items = deps.split_items_without_deps(items)
        self.assertEqual(removed_items, [])
        self.assertEqual(items, [item1, item2, item3])

    def test_no_deps(self):
        class FakeItem(object):
            pass
        item1 = FakeItem()
        item1._deps = []
        item2 = FakeItem()
        item2._deps = []
        item3 = FakeItem()
        item3._deps = []
        items = [item1, item2, item3]
        items, removed_items = deps.split_items_without_deps(items)
        self.assertEqual(items, [])
        self.assertEqual(removed_items, [item1, item2, item3])

    def test_some_deps(self):
        class FakeItem(object):
            pass
        item1 = FakeItem()
        item1._deps = []
        item2 = FakeItem()
        item2._deps = []
        item3 = FakeItem()
        item3._deps = ["type2:"]
        items = [item1, item2, item3]
        items, removed_items = deps.split_items_without_deps(items)
        self.assertEqual(removed_items, [item1, item2])
        self.assertEqual(items, [item3])


class ItemsRemoveDepTest(TestCase):
    """
    Tests blockwart.deps.remove_dep_from_items.
    """
    def test_remove(self):
        item1 = MagicMock()
        item1._deps = ["foo", "bar"]
        item2 = MagicMock()
        item2._deps = ["foo"]
        items = deps.remove_dep_from_items([item1, item2], "foo")
        self.assertEqual(items[0]._deps, ["bar"])
        self.assertEqual(items[1]._deps, [])


class RemoveItemDependentsTest(TestCase):
    """
    Tests blockwart.deps.remove_item_dependents.
    """
    def test_remove_empty(self):
        self.assertEqual(deps.remove_item_dependents([], "foo"), ([], []))

    def test_recursive_removal(self):
        item1 = MagicMock()
        item1.id = "item1"
        item1._deps = ["item2"]
        item2 = MagicMock()
        item2.id = "item2"
        item2._deps = ["item3"]
        item3 = MagicMock()
        item3.id = "item3"
        item3._deps = []
        items = [item1, item2, item3]

        self.assertEqual(
            deps.remove_item_dependents(items, "item3"),
            ([item3], [item2, item1]),
        )
