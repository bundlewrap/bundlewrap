from unittest import TestCase

from mock import MagicMock, patch

from blockwart.bundle import Bundle
from blockwart.items import Item
from blockwart.exceptions import RepositoryError
from blockwart.utils import names


class BundleInitTest(TestCase):
    """
    Tests initialization of blockwart.bundle.Bundle.
    """
    @patch('blockwart.bundle.validate_name', return_value=False)
    def test_bad_bundle_name(self, *args):
        with self.assertRaises(RepositoryError):
            Bundle(MagicMock(), "name")

    def test_unknown_bundle(self, *args):
        repo = MagicMock()
        repo.bundle_names = []
        with self.assertRaises(RepositoryError):
            Bundle(repo, "name")


class BundleItemsTest(TestCase):
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

        class MyOtherItem(Item):
            BUNDLE_ATTRIBUTE_NAME = 'attr3'
            ITEM_TYPE_NAME = 'mystuff3'

        node = MagicMock()
        node.repo.bundle_names = ("mybundle",)
        node.repo.item_classes = (MyItem, MyOtherItem)
        b = Bundle(node, "mybundle")
        self.assertEqual(set(names(b.items)), set(('name1', 'name2')))
