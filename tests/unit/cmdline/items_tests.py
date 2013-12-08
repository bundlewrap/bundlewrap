from unittest import TestCase

from mock import MagicMock

from blockwart.cmdline import items


class MockItem(object):
    def __init__(self, name):
        self.id = name

    def __str__(self):
        return self.id


class ItemsTest(TestCase):
    """
    Tests blockwart.cmdline.items.bw_items.
    """
    def setUp(self):
        item1 = MockItem("type1:item1")
        item2 = MockItem("type1:item2")
        item3 = MockItem("directory:/bar/baz")
        item4 = MockItem("file:/foo/47")

        node = MagicMock()
        node.items = (item1, item2, item3, item4)

        self.repo = MagicMock()
        self.repo.get_node.return_value = node

    def test_simple_item_list(self):
        args = MagicMock()
        args.node = "node1"
        output = list(items.bw_items(self.repo, args))
        self.assertEqual(
            output,
            [
                "type1:item1",
                "type1:item2",
                "directory:/bar/baz",
                "file:/foo/47",
            ],
        )

