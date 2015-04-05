from unittest import TestCase

try:
    from unittest.mock import MagicMock, patch
except ImportError:
    from mock import MagicMock, patch

from bundlewrap.bundle import Bundle
from bundlewrap.items import Item
from bundlewrap.exceptions import NoSuchBundle, RepositoryError
from bundlewrap.node import Node
from bundlewrap.repo import Repository
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


class BundleGeneratedItemsTest(TestCase):
    """
    Tests bundlewrap.bundle.Bundle._generated_items.
    """
    @patch('bundlewrap.bundle.get_all_attrs_from_file')
    def test_generated_items(self, get_all_attrs_from_file):
        def my_item_generator(node, bundle, item):
            generated_items = {'files': {}}
            if item.ITEM_TYPE_NAME == 'user':
                file_path = "/home/{}/.screenrc".format(item.name)
                generated_items['files'][file_path] = {
                    'content': "foo",
                }
            return generated_items

        get_all_attrs_from_file.return_value = {
            'item_generators': [
                'test.generator',
            ],
            'users': {
                'jdoe': {},
            },
        }
        repo = Repository()
        repo.bundle_names = ["generatingbundle"]
        repo.libs = MagicMock()
        repo.libs.test.generator = my_item_generator
        node = Node("node1", {'bundles': ["generatingbundle"]})
        repo.add_node(node)
        self.assertEqual(len(node.bundles[0]._generated_items), 1)
        generated_item = node.bundles[0]._generated_items[0]
        self.assertEqual(generated_item.id, "file:/home/jdoe/.screenrc")
