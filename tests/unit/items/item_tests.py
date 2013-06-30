from unittest import TestCase

from mock import MagicMock, patch

from blockwart.items import Item
from blockwart.exceptions import BundleError


class InitTest(TestCase):
    """
    Tests initialization of blockwart.items.Item.
    """
    @patch('blockwart.items.Item._validate_attribute_names')
    @patch('blockwart.items.Item.validate_attributes')
    def test_init_no_validation(self, validate_names, validate_values):
        bundle = MagicMock()
        i = Item(bundle, "item1", {}, skip_validation=True)
        self.assertEqual(i.bundle, bundle)
        self.assertEqual(i.name, "item1")
        self.assertFalse(validate_names.called)
        self.assertFalse(validate_values.called)

    @patch('blockwart.items.Item._validate_attribute_names')
    @patch('blockwart.items.Item.validate_attributes')
    def test_init_with_validation(self, validate_names, validate_values):
        Item(MagicMock(), MagicMock(), {}, skip_validation=False)
        self.assertTrue(validate_names.called)
        self.assertTrue(validate_values.called)

    def test_attribute_name_validation_ok(self):
        item = Item(MagicMock(), MagicMock(), {}, skip_validation=True)
        item.ITEM_ATTRIBUTES = {'foo': 47, 'bar': 48}
        item._validate_attribute_names({'foo': 49, 'depends': []})

    def test_attribute_name_validation_fail(self):
        item = Item(MagicMock(), "item1", {}, skip_validation=True)
        item.ITEM_ATTRIBUTES = {'foo': 47, 'bar': 48}
        with self.assertRaises(BundleError):
            item._validate_attribute_names({
                'foobar': 49,
                'bar': 50,
                'depends': [],
            })

    def test_subclass_attributes(self):
        class MyItem(Item):
            ITEM_ATTRIBUTES = {'foo': 47, 'bar': 48}

        i = MyItem(MagicMock(), MagicMock(), {'foo': 49})
        self.assertEqual(i.attributes, {'foo': 49, 'bar': 48})
