from unittest import TestCase

from mock import MagicMock, patch

from blockwart.exceptions import ItemDependencyError, RepositoryError
from blockwart.group import Group
from blockwart.items import Item, ItemStatus
from blockwart.node import ApplyResult, apply_items, DummyItem, flatten_dependencies, \
    inject_concurrency_blockers, inject_dummy_items, Node, remove_dep_from_items, \
    remove_item_dependents, split_items_without_deps
from blockwart.repo import Repository
from blockwart.utils import names


class MockNode(object):
    pass


class MockBundle(object):
    bundle_dir = ""


class MockItemStatus(object):
    pass


class MockItem(Item):
    BUNDLE_ATTRIBUTE_NAME = "mock"
    ITEM_TYPE_NAME = "type1"
    DEPENDS_STATIC = []

    def apply(self, *args, **kwargs):
        status = MockItemStatus()
        status.correct = True
        status._name = self.name
        return (status, status)
del Item.__reduce__  # we don't need the custom pickle-magic for our
                     # MockItems


def get_mock_item(itype, name, deps_static, deps):
    bundle = MockBundle()
    bundle.node = MockNode()
    item = MockItem(bundle, name, {'depends': deps}, skip_validation=True)
    item.ITEM_TYPE_NAME = itype
    item.DEPENDS_STATIC = deps_static
    item.PARALLEL_APPLY = True
    return item


class ApplyItemsTest(TestCase):
    """
    Tests blockwart.node.apply_items.
    """
    def test_self_loop(self):
        i1 = get_mock_item("type1", "name1", [], ["type1:name1"])
        i2 = get_mock_item("type1", "name2", [], [])
        node = MagicMock()
        node.items = [i1, i2]
        with self.assertRaises(ItemDependencyError):
            list(apply_items(node))

    def test_direct_loop(self):
        i1 = get_mock_item("type1", "name1", [], ["type1:name2"])
        i2 = get_mock_item("type1", "name2", [], ["type1:name1"])
        node = MagicMock()
        node.items = [i1, i2]
        with self.assertRaises(ItemDependencyError):
            list(apply_items(node))

    def test_nested_loop(self):
        i1 = get_mock_item("type1", "name1", [], ["type1:name2"])
        i2 = get_mock_item("type1", "name2", [], ["type1:name3"])
        i3 = get_mock_item("type1", "name3", [], ["type1:name4"])
        i4 = get_mock_item("type1", "name4", [], ["type1:name1"])
        node = MagicMock()
        node.items = [i1, i2, i3, i4]
        with self.assertRaises(ItemDependencyError):
            list(apply_items(node))

    def test_implicit_loop(self):
        i1 = get_mock_item("type1", "name1", [], ["type1:name2"])
        i2 = get_mock_item("type1", "name2", [], ["type1:"])
        node = MagicMock()
        node.items = [i1, i2]
        with self.assertRaises(ItemDependencyError):
            list(apply_items(node))

    def test_simple_order(self):
        i1 = get_mock_item("type1", "name1", [], ["type1:name2"])
        i2 = get_mock_item("type1", "name2", [], ["type1:name3"])
        i3 = get_mock_item("type1", "name3", [], [])

        node = MagicMock()
        node.items = [i1, i2, i3]

        results = list(apply_items(node))

        self.assertEqual(results[0][1]._name, "name3")
        self.assertEqual(results[1][1]._name, "name2")
        self.assertEqual(results[2][1]._name, "name1")


    def test_implicit_order(self):
        i1 = get_mock_item("type1", "name1", [], ["type1:name2"])
        i2 = get_mock_item("type1", "name2", [], [])
        i3 = get_mock_item("type2", "name3", ["type1:"], [])

        node = MagicMock()
        node.items = [i1, i2, i3]

        results = list(apply_items(node))

        self.assertEqual(results[0][1]._name, "name2")
        self.assertEqual(results[1][1]._name, "name1")
        self.assertEqual(results[2][1]._name, "name3")

    def test_apply_parallel(self):
        i1 = get_mock_item("type1", "name1", [], ["type1:name2"])
        i2 = get_mock_item("type1", "name2", [], ["type1:name3"])
        i3 = get_mock_item("type1", "name3", [], [])

        node = MagicMock()
        node.items = [i1, i2, i3]

        results = list(apply_items(node, workers=2))

        self.assertEqual(results[0][1]._name, "name3")
        self.assertEqual(results[1][1]._name, "name2")
        self.assertEqual(results[2][1]._name, "name1")


    def test_apply_interactive(self):
        i1 = get_mock_item("type1", "name1", [], ["type1:name2"])
        i2 = get_mock_item("type1", "name2", [], ["type1:name3"])
        i3 = get_mock_item("type1", "name3", [], [])

        node = MagicMock()
        node.items = [i1, i2, i3]

        results = list(apply_items(node, interactive=True))

        self.assertEqual(results[0][1]._name, "name3")
        self.assertEqual(results[1][1]._name, "name2")
        self.assertEqual(results[2][1]._name, "name1")


class ApplyResultTest(TestCase):
    """
    Tests blockwart.node.ApplyResult.
    """
    def test_correct(self):
        item_results = (
            (ItemStatus(correct=True), ItemStatus(correct=True)),
        )
        output_result = ApplyResult(MagicMock(), item_results, [])
        self.assertEqual(output_result.correct, 1)
        self.assertEqual(output_result.fixed, 0)
        self.assertEqual(output_result.skipped, 0)
        self.assertEqual(output_result.unfixable, 0)
        self.assertEqual(output_result.failed, 0)

    def test_fixed(self):
        item_results = (
            (ItemStatus(correct=False), ItemStatus(correct=True)),
        )
        output_result = ApplyResult(MagicMock(), item_results, [])
        self.assertEqual(output_result.correct, 0)
        self.assertEqual(output_result.fixed, 1)
        self.assertEqual(output_result.skipped, 0)
        self.assertEqual(output_result.unfixable, 0)
        self.assertEqual(output_result.failed, 0)

    def test_skipped(self):
        after = ItemStatus(correct=False)
        after.skipped = True
        item_results = (
            (ItemStatus(correct=False), after),
        )
        output_result = ApplyResult(MagicMock(), item_results, [])
        self.assertEqual(output_result.correct, 0)
        self.assertEqual(output_result.fixed, 0)
        self.assertEqual(output_result.skipped, 1)
        self.assertEqual(output_result.unfixable, 0)
        self.assertEqual(output_result.failed, 0)

    def test_unfixable(self):
        item_results = (
            (ItemStatus(correct=False), ItemStatus(correct=False,
                                                   fixable=False)),
        )
        output_result = ApplyResult(MagicMock(), item_results, [])
        self.assertEqual(output_result.correct, 0)
        self.assertEqual(output_result.fixed, 0)
        self.assertEqual(output_result.skipped, 0)
        self.assertEqual(output_result.unfixable, 1)
        self.assertEqual(output_result.failed, 0)

    def test_failed(self):
        item_results = (
            (ItemStatus(correct=False), ItemStatus(correct=False)),
        )
        output_result = ApplyResult(MagicMock(), item_results, [])
        self.assertEqual(output_result.correct, 0)
        self.assertEqual(output_result.fixed, 0)
        self.assertEqual(output_result.skipped, 0)
        self.assertEqual(output_result.unfixable, 0)
        self.assertEqual(output_result.failed, 1)

    def test_bs(self):
        item_results = (
            (ItemStatus(correct=True), ItemStatus(correct=False)),
        )
        with self.assertRaises(RuntimeError):
            ApplyResult(MagicMock(), item_results, [])


class FlattenDependenciesTest(TestCase):
    """
    Tests blockwart.node.flatten_dependencies.
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

        items = flatten_dependencies(items)

        deps_should = {
            item1: [],
            item2: [],
            item3: ["type1:", "type1:name1", "type1:name2"],
            item4: ["type1:", "type1:name1", "type1:name2", "type2:name1"],
            item5: ["type1:name1", "type1:name2"],
        }

        for item in items:
            self.assertEqual(set(item._flattened_deps), set(deps_should[item]))


class InitTest(TestCase):
    """
    Tests initialization of blockwart.node.Node.
    """
    @patch('blockwart.node.validate_name', return_value=False)
    def test_bad_bundle_name(self, *args):
        with self.assertRaises(RepositoryError):
            Node("name")


class InjectDummyItemsTest(TestCase):
    """
    Tests blockwart.node.inject_dummy_items.
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

        injected = inject_dummy_items(items)

        dummy_counter = 0
        for item in injected:
            if isinstance(item, DummyItem):
                self.assertTrue(len(item._deps) > 0)
                dummy_counter += 1
                for dep in item._deps:
                    self.assertTrue(dep.startswith(item.id))
        self.assertEqual(len(injected), 7)
        self.assertEqual(dummy_counter, 3)


class InjectConcurrencyBlockersTest(TestCase):
    """
    Tests blockwart.node.inject_concurrency_blockers.
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
        injected = inject_concurrency_blockers(items)

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
        injected = inject_concurrency_blockers(items)

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


class ItemOrderTest(TestCase):
    """
    Tests blockwart.node.order_items.
    """
    class FakeItem1(Item):
        DEPENDS_STATIC = []
        ITEM_TYPE_NAME = "type1"

        def apply(self, *args, **kwargs):
            return self.name


class ItemSplitWithoutDepTest(TestCase):
    """
    Tests blockwart.node.split_items_without_deps.
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
        items, removed_items = split_items_without_deps(items)
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
        items, removed_items = split_items_without_deps(items)
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
        items, removed_items = split_items_without_deps(items)
        self.assertEqual(removed_items, [item1, item2])
        self.assertEqual(items, [item3])


class ItemsRemoveDepTest(TestCase):
    """
    Tests blockwart.node.remove_dep_from_items.
    """
    def test_remove(self):
        item1 = MagicMock()
        item1._deps = ["foo", "bar"]
        item2 = MagicMock()
        item2._deps = ["foo"]
        items = remove_dep_from_items([item1, item2], "foo")
        self.assertEqual(items[0]._deps, ["bar"])
        self.assertEqual(items[1]._deps, [])


class RemoveItemDependentsTest(TestCase):
    """
    Tests blockwart.node.remove_item_dependents.
    """
    def test_remove_empty(self):
        self.assertEqual(remove_item_dependents([], "foo"), ([], []))

    def test_recursive_removal(self):
        item1 = MagicMock()
        item1.id = "item1"
        item1.depends = ["item2"]
        item2 = MagicMock()
        item2.id = "item2"
        item2.depends = ["item3"]
        item3 = MagicMock()
        item3.id = "item3"
        item3.depends = []
        items = [item1, item2, item3]

        self.assertEqual(
            remove_item_dependents(items, "item3"),
            ([item3], [item2, item1]),
        )


class NodeTest(TestCase):
    """
    Tests blockwart.node.Node.
    """
    @patch('blockwart.node.ApplyResult')
    @patch('blockwart.node.NodeLock')
    @patch('blockwart.node.run_actions')
    @patch('blockwart.node.apply_items')
    def test_apply(self, apply_items, run_actions, NodeLock, ApplyResult):
        repo = Repository()
        n = Node("node1", {})
        repo.add_node(n)
        result = MagicMock()
        ApplyResult.return_value = result
        NodeLock.__enter__ = lambda x: x
        NodeLock.__exit__ = lambda x: x
        self.assertEqual(n.apply(), result)
        self.assertEqual(apply_items.call_count, 1)
        self.assertEqual(run_actions.call_count, 4)
        ApplyResult.assert_called_once()

    def test_bundles(self):
        repo = Repository()
        repo.bundle_names = ("bundle1", "bundle2", "bundle3")
        n = Node("node1", {})
        repo.add_node(n)
        g1 = Group("group1", {'bundles': ("bundle1", "bundle2")})
        repo.add_group(g1)
        g2 = Group("group2", {'bundles': ("bundle3",)})
        repo.add_group(g2)
        with patch('tests.unit.node_tests.Node.groups', new=(g1, g2)):
            self.assertEqual(
                tuple(names(n.bundles)),
                ("bundle1", "bundle2", "bundle3"),
            )

    def test_hostname_defaults(self):
        n = Node("node1", {})
        self.assertEqual(n.hostname, "node1")
        n = Node("node2", {'hostname': "node2.example.com"})
        self.assertEqual(n.hostname, "node2.example.com")
