# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from unittest import TestCase

try:
    from unittest.mock import MagicMock, patch
except ImportError:
    from mock import MagicMock, patch

from bundlewrap.exceptions import ItemDependencyError, NodeAlreadyLockedException, RepositoryError
from bundlewrap.group import Group
from bundlewrap.items import Item
from bundlewrap.node import ApplyResult, apply_items, _flatten_group_hierarchy, Node, NodeLock
from bundlewrap.operations import RunResult
from bundlewrap.repo import Repository
from bundlewrap.utils import names


class MockNode(object):
    name = "mocknode"


class MockBundle(object):
    name = "mock"
    bundle_dir = ""
    bundle_data_dir = ""
    items = []


class MockItem(Item):
    BUNDLE_ATTRIBUTE_NAME = "mock"
    ITEM_TYPE_NAME = "type1"
    NEEDS_STATIC = []
    _APPLY_RESULT = Item.STATUS_OK

    def apply(self, *args, **kwargs):
        return self._APPLY_RESULT
del Item.__reduce__  # we don't need the custom pickle-magic for our
                     # MockItems


def get_mock_item(itype, name, deps_static, deps):
    bundle = MockBundle()
    bundle.node = MockNode()
    item = MockItem(bundle, name, {'needs': deps}, skip_validation=True)
    item.ITEM_TYPE_NAME = itype
    item.NEEDS_STATIC = deps_static
    return item


class ApplyItemsTest(TestCase):
    """
    Tests bundlewrap.node.apply_items.
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

        self.assertEqual(results[0][0], "type1:name3")
        self.assertEqual(results[1][0], "type1:name2")
        self.assertEqual(results[2][0], "type1:name1")

    def test_implicit_order(self):
        i1 = get_mock_item("type1", "name1", [], ["type1:name2"])
        i2 = get_mock_item("type1", "name2", [], [])
        i3 = get_mock_item("type2", "name3", ["type1:"], [])

        node = MagicMock()
        node.items = [i1, i2, i3]

        results = list(apply_items(node))

        self.assertEqual(results[0][0], "type1:name2")
        self.assertEqual(results[1][0], "type1:name1")
        self.assertEqual(results[2][0], "type2:name3")

    def test_apply_parallel(self):
        i1 = get_mock_item("type1", "name1", [], ["type1:name2"])
        i2 = get_mock_item("type1", "name2", [], ["type1:name3"])
        i3 = get_mock_item("type1", "name3", [], [])

        node = MagicMock()
        node.items = [i1, i2, i3]

        results = list(apply_items(node, workers=2))

        self.assertEqual(results[0][0], "type1:name3")
        self.assertEqual(results[1][0], "type1:name2")
        self.assertEqual(results[2][0], "type1:name1")

    def test_apply_interactive(self):
        i1 = get_mock_item("type1", "name1", [], ["type1:name2"])
        i2 = get_mock_item("type1", "name2", [], ["type1:name3"])
        i3 = get_mock_item("type1", "name3", [], [])

        node = MagicMock()
        node.items = [i1, i2, i3]

        results = list(apply_items(node, interactive=True, profiling=True))

        self.assertEqual(results[0][0], "type1:name3")
        self.assertEqual(results[1][0], "type1:name2")
        self.assertEqual(results[2][0], "type1:name1")


class ApplyResultTest(TestCase):
    """
    Tests bundlewrap.node.ApplyResult.
    """
    def test_correct(self):
        item_results = (
            ("item_id", Item.STATUS_OK, None),
        )
        output_result = ApplyResult(MagicMock(), item_results)
        self.assertEqual(output_result.correct, 1)
        self.assertEqual(output_result.fixed, 0)
        self.assertEqual(output_result.skipped, 0)
        self.assertEqual(output_result.failed, 0)

    def test_fixed(self):
        item_results = (
            ("item_id", Item.STATUS_FIXED, None),
        )
        output_result = ApplyResult(MagicMock(), item_results)
        self.assertEqual(output_result.correct, 0)
        self.assertEqual(output_result.fixed, 1)
        self.assertEqual(output_result.skipped, 0)
        self.assertEqual(output_result.failed, 0)

    def test_skipped(self):
        item_results = (
            ("item_id", Item.STATUS_SKIPPED, None),
        )
        output_result = ApplyResult(MagicMock(), item_results)
        self.assertEqual(output_result.correct, 0)
        self.assertEqual(output_result.fixed, 0)
        self.assertEqual(output_result.skipped, 1)
        self.assertEqual(output_result.failed, 0)

    def test_failed(self):
        item_results = (
            ("item_id", Item.STATUS_FAILED, None),
        )
        output_result = ApplyResult(MagicMock(), item_results)
        self.assertEqual(output_result.correct, 0)
        self.assertEqual(output_result.fixed, 0)
        self.assertEqual(output_result.skipped, 0)
        self.assertEqual(output_result.failed, 1)

    def test_bs(self):
        item_results = (
            ("item_id", 777, None),
        )
        with self.assertRaises(RuntimeError):
            ApplyResult(MagicMock(), item_results)


class FlattenGroupHierarchyTest(TestCase):
    """
    Tests bundlewrap.node._flatten_group_hierarchy.
    """
    def test_reorder_chain(self):
        group1 = MagicMock()
        group1.name = "group1"
        group2 = MagicMock()
        group2.name = "group2"
        group3 = MagicMock()
        group3.name = "group3"

        group3.subgroups = [group2]
        group2.subgroups = [group1]
        group1.subgroups = []

        self.assertEqual(
            _flatten_group_hierarchy([group1, group2, group3]),
            ["group3", "group2", "group1"],
        )

    def test_reorder_short_chain(self):
        group1 = MagicMock()
        group1.name = "group1"
        group2 = MagicMock()
        group2.name = "group2"
        group3 = MagicMock()
        group3.name = "group3"

        group3.subgroups = [group2]
        group2.subgroups = []
        group1.subgroups = []

        order = _flatten_group_hierarchy([group1, group2, group3])
        self.assertTrue(order.index("group3") < order.index("group2"))

    def test_loop(self):
        group1 = MagicMock()
        group1.name = "group1"
        group2 = MagicMock()
        group2.name = "group2"
        group3 = MagicMock()
        group3.name = "group3"

        group3.subgroups = [group2]
        group2.subgroups = [group1]
        group1.subgroups = [group3]

        with self.assertRaises(RuntimeError):
            _flatten_group_hierarchy([group1, group2, group3])


class InitTest(TestCase):
    """
    Tests initialization of bundlewrap.node.Node.
    """
    @patch('bundlewrap.node.validate_name', return_value=False)
    def test_bad_bundle_name(self, *args):
        with self.assertRaises(RepositoryError):
            Node("name")


class NodeTest(TestCase):
    """
    Tests bundlewrap.node.Node.
    """
    @patch('bundlewrap.node.ApplyResult')
    @patch('bundlewrap.node.NodeLock')
    @patch('bundlewrap.node.apply_items')
    def test_apply(self, apply_items, NodeLock, ApplyResult):
        repo = Repository()
        n = Node("node1", {})
        repo.add_node(n)
        result = MagicMock()
        ApplyResult.return_value = result
        NodeLock.__enter__ = lambda x: x
        NodeLock.__exit__ = lambda x: x
        self.assertEqual(n.apply(), result)
        self.assertEqual(apply_items.call_count, 1)
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


class NodeLockTest(TestCase):
    """
    Tests bundlewrap.node.NodeLock.
    """
    @patch('bundlewrap.node.ask_interactively')
    def test_locked(self, ask_interactively):
        node = MagicMock()
        runres = RunResult()
        runres.return_code = 1
        node.run.return_value = runres
        with self.assertRaises(NodeAlreadyLockedException):
            with NodeLock(node, False, ignore=False):
                pass
