from unittest import TestCase

from mock import MagicMock, patch

from bundlewrap.bundle import Bundle
from bundlewrap.items import Item
from bundlewrap.exceptions import NoSuchBundle, RepositoryError
from bundlewrap.utils import names


class BundleInitTest(TestCase):
    """
    Tests initialization of bundlewrap.bundle.Bundle.
    """
    def test_bad_bundle_name(self, *args):
        with self.assertRaises(RepositoryError):
            Bundle(MagicMock(), "invalid name")

    def test_unknown_bundle(self, *args):
        repo = MagicMock()
        repo.bundle_names = []
        with self.assertRaises(NoSuchBundle):
            Bundle(repo, "name")


class BundleItemsTest(TestCase):
    """
    Tests bundlewrap.bundle.Bundle.items.
    """
    @patch('bundlewrap.bundle.get_all_attrs_from_file', return_value={
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
