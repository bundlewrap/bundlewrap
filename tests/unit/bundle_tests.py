from unittest import TestCase

from mock import MagicMock, patch

from blockwart.bundle import Bundle
from blockwart.items import Item
from blockwart.exceptions import RepositoryError
from blockwart.utils import names


class InitTest(TestCase):
    """
    Tests initialization of blockwart.bundle.Bundle.
    """
    @patch('blockwart.bundle.validate_name', return_value=False)
    def test_bad_bundle_name(self, *args):
        with self.assertRaises(RepositoryError):
            Bundle(MagicMock(), "name")


class ItemsTest(TestCase):
    """
    Tests blockwart.bundle.Bundle.items.
    """
    @patch('blockwart.bundle.get_all_attrs_from_file', return_value={
        'attr1': {'name1': {}, 'name2': {}},
        'attr2': {'name3': {}},
    })
    def test_items(self, *args):
        class MyItem(Item):
            BUNDLE_ATTRIBUTE_NAME = 'attr1'
            ITEM_TYPE_NAME = 'mystuff'
        node = MagicMock()
        node.repo = MagicMock()
        node.repo.bundle_names = ("mybundle",)
        node.repo.item_classes = (MyItem,)
        b = Bundle(node, "mybundle")
        self.assertEqual(set(names(b.items)), set(('name1', 'name2')))
