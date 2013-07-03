from unittest import TestCase

from mock import MagicMock, patch

from blockwart.exceptions import ItemDependencyError, RepositoryError
from blockwart.group import Group
from blockwart.node import Node, order_items, split_items_without_deps, \
    remove_dep_from_items
from blockwart.utils import names


class InitTest(TestCase):
    """
    Tests initialization of blockwart.node.Node.
    """
    @patch('blockwart.node.validate_name', return_value=False)
    def test_bad_bundle_name(self, *args):
        with self.assertRaises(RepositoryError):
            Node(MagicMock(), "name")


class ItemOrderTest(TestCase):
    """
    Tests blockwart.node.order_items.
    """
    class FakeItem(object):
        DEPENDS_STATIC = []

        def __init__(self, type_name, name):
            self.ITEM_TYPE_NAME = type_name
            self.name = name
            self.id = "{}:{}".format(self.ITEM_TYPE_NAME, self.name)
            self.depends = []

    def test_self_loop(self):
        i1 = self.FakeItem("type1", "name1")
        i1.depends = ["type1:name1"]
        i2 = self.FakeItem("type1", "name2")
        with self.assertRaises(ItemDependencyError):
            order_items([i1, i2])

    def test_direct_loop(self):
        i1 = self.FakeItem("type1", "name1")
        i1.depends = ["type1:name2"]
        i2 = self.FakeItem("type1", "name2")
        i2.depends = ["type1:name1"]
        with self.assertRaises(ItemDependencyError):
            order_items([i1, i2])

    def test_nested_loop(self):
        i1 = self.FakeItem("type1", "name1")
        i1.depends = ["type1:name2"]
        i2 = self.FakeItem("type1", "name2")
        i2.depends = ["type1:name3"]
        i3 = self.FakeItem("type1", "name3")
        i3.depends = ["type1:name4"]
        i4 = self.FakeItem("type1", "name4")
        i4.depends = ["type1:name1"]
        with self.assertRaises(ItemDependencyError):
            order_items([i1, i2, i3, i4])

    def test_implicit_loop(self):
        i1 = self.FakeItem("type1", "name1")
        i1.depends = ["type2:name2"]
        i2 = self.FakeItem("type2", "name2")
        i2.DEPENDS_STATIC = ["type1:"]
        with self.assertRaises(ItemDependencyError):
            order_items([i1, i2])

    def test_simple_order(self):
        i1 = self.FakeItem("type1", "name1")
        i1.depends = ["type1:name2"]
        i2 = self.FakeItem("type1", "name2")
        i2.depends = ["type1:name3"]
        i3 = self.FakeItem("type1", "name3")
        expected_result = [i3, i2, i1]
        self.assertEqual(order_items([i1, i2, i3]), expected_result)
        self.assertEqual(order_items([i2, i1, i3]), expected_result)
        self.assertEqual(order_items([i3, i2, i1]), expected_result)
        self.assertEqual(order_items([i2, i3, i1]), expected_result)
        self.assertEqual(order_items([i3, i1, i2]), expected_result)
        self.assertEqual(order_items([i1, i3, i2]), expected_result)

    def test_implicit_order(self):
        i1 = self.FakeItem("type1", "name1")
        i1.depends = ["type1:name2"]
        i2 = self.FakeItem("type1", "name2")
        i3 = self.FakeItem("type2", "name1")
        i3.DEPENDS_STATIC = ["type1:"]
        expected_result = [i2, i1, i3]
        self.assertEqual(order_items([i1, i2, i3]), expected_result)
        self.assertEqual(order_items([i2, i1, i3]), expected_result)
        self.assertEqual(order_items([i3, i2, i1]), expected_result)
        self.assertEqual(order_items([i2, i3, i1]), expected_result)
        self.assertEqual(order_items([i3, i1, i2]), expected_result)
        self.assertEqual(order_items([i1, i3, i2]), expected_result)


class ItemSplitWithoutDepTest(TestCase):
    """
    Tests blockwart.node.split_items_without_deps.
    """
    def test_all_deps(self):
        class FakeItem(object):
            pass
        item1 = FakeItem()
        item1.DEPENDS_STATIC = []
        item1.depends = ["type1:name1"]
        item2 = FakeItem()
        item2.DEPENDS_STATIC = ["type1:"]
        item2.depends = ["type2:name2"]
        item3 = FakeItem()
        item3.DEPENDS_STATIC = ["type2:"]
        item3.depends = []
        items = [item1, item2, item3]
        items, removed_items = split_items_without_deps(items)
        self.assertEqual(removed_items, [])
        self.assertEqual(items, [item1, item2, item3])

    def test_no_deps(self):
        class FakeItem(object):
            pass
        item1 = FakeItem()
        item1.DEPENDS_STATIC = []
        item1.depends = []
        item2 = FakeItem()
        item2.DEPENDS_STATIC = []
        item2.depends = []
        item3 = FakeItem()
        item3.DEPENDS_STATIC = []
        item3.depends = []
        items = [item1, item2, item3]
        items, removed_items = split_items_without_deps(items)
        self.assertEqual(items, [])
        self.assertEqual(removed_items, [item1, item2, item3])

    def test_some_deps(self):
        class FakeItem(object):
            pass
        item1 = FakeItem()
        item1.DEPENDS_STATIC = []
        item1.depends = []
        item2 = FakeItem()
        item2.DEPENDS_STATIC = []
        item2.depends = []
        item3 = FakeItem()
        item3.DEPENDS_STATIC = ["type2:"]
        item3.depends = []
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


class NodeTest(TestCase):
    """
    Tests blockwart.node.Node.
    """
    def test_bundles(self):
        repo = MagicMock()
        repo.bundle_names = ("bundle1", "bundle2", "bundle3")
        n = Node(repo, "node1", {})
        g1 = Group(None, "group1", {'bundles': ("bundle1", "bundle2")})
        g2 = Group(None, "group2", {'bundles': ("bundle3",)})
        with patch('tests.unit.node_tests.Node.groups', new=(g1, g2)):
            self.assertEqual(
                tuple(names(n.bundles)),
                ("bundle1", "bundle2", "bundle3"),
            )

    def test_hostname_defaults(self):
        n = Node(None, "node1", {})
        self.assertEqual(n.hostname, "node1")
        n = Node(None, "node2", {'hostname': "node2.example.com"})
        self.assertEqual(n.hostname, "node2.example.com")
