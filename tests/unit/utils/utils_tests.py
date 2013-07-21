from os.path import join
from shutil import rmtree
from tempfile import mkdtemp
from unittest import TestCase

from mock import patch

from blockwart import utils
from blockwart.utils import text


class CachedPropertyTest(TestCase):
    """
    Tests blockwart.utils.cached_property.
    """
    def test_called_once(self):
        class ExampleClass(object):
            def __init__(self):
                self.counter = 0

            @utils.cached_property
            def testprop(self):
                self.counter += 1
                return self.counter

        obj = ExampleClass()

        self.assertEqual(obj.testprop, 1)
        # a standard property would now return 2
        self.assertEqual(obj.testprop, 1)


class GetAttrFromFileTest(TestCase):
    """
    Tests blockwart.utils.getattr_from_file and .get_all_attrs_from_file.
    """
    def setUp(self):
        self.tmpdir = mkdtemp()
        self.fname = join(self.tmpdir, "test.py")

    def tearDown(self):
        rmtree(self.tmpdir)

    @patch('blockwart.utils.get_file_contents', return_value="c = 47")
    def test_cache_enabled(self, *args):
        utils.getattr_from_file(self.fname, 'c')
        utils.getattr_from_file(self.fname, 'c')
        utils.get_file_contents.assert_called_once_with(self.fname)

    @patch('blockwart.utils.get_file_contents', return_value="c = 47")
    def test_cache_disabled(self, *args):
        utils.getattr_from_file(self.fname, 'c', cache_write=False)
        utils.getattr_from_file(self.fname, 'c')
        self.assertEqual(utils.get_file_contents.call_count, 2)

    @patch('blockwart.utils.get_file_contents', return_value="c = 47")
    def test_cache_ignore(self, *args):
        self.assertEqual(
            utils.getattr_from_file(self.fname, 'c'),
            47,
        )
        utils.get_file_contents.return_value = "c = 48"
        self.assertEqual(
            utils.getattr_from_file(self.fname, 'c', cache_read=False),
            48,
        )
        self.assertEqual(utils.get_file_contents.call_count, 2)

    def test_default(self):
        with open(join(self.tmpdir, self.fname), 'w') as f:
            f.write("")
        with self.assertRaises(KeyError):
            utils.getattr_from_file(self.fname, 'c')
        self.assertEqual(
            utils.getattr_from_file(self.fname, 'c', default=None),
            None,
        )
        self.assertEqual(
            utils.getattr_from_file(self.fname, 'c', default=49),
            49,
        )

    def test_import(self):
        with open(join(self.tmpdir, self.fname), 'w') as f:
            f.write("c = 47")
        self.assertEqual(
            utils.getattr_from_file(self.fname, 'c', cache_read=False),
            47,
        )
        return
        with open(join(self.tmpdir, self.fname), 'w') as f:
            f.write("c = 48")
        self.assertEqual(
            utils.getattr_from_file(self.fname, 'c'), 48)


class NamesTest(TestCase):
    """
    Tests blockwart.utils.names.
    """
    def test_names(self):
        class TestObj(object):
            def __init__(self, name):
                self.name = name

        l = (TestObj("obj1"), TestObj("obj2"))
        self.assertEqual(list(utils.names(l)), ["obj1", "obj2"])


class NameValidationTest(TestCase):
    """
    Tests blockwart.utils.text.validate_name.
    """
    def test_good_names(self):
        for name in (
            "foo",
            "foo-bar2",
            "foo_bar",
            "foo.bar",
            "foo...",
        ):
            self.assertTrue(text.validate_name(name))

    def test_bad_names(self):
        for name in (
            ".foo",
            "foo!bar",
            "foo,bar",
            "foo;bar",
        ):
            self.assertFalse(text.validate_name(name))
