from os.path import join
from shutil import rmtree
from tempfile import mkdtemp
from unittest import TestCase

from mock import MagicMock, patch

from bundlewrap import utils
from bundlewrap.metadata import atomic


class CachedPropertyTest(TestCase):
    """
    Tests bundlewrap.utils.cached_property.
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


class DownloadTest(TestCase):
    def setUp(self):
        self.tmpdir = mkdtemp()
        self.fname = join(self.tmpdir, "foodir/testfile")

    def tearDown(self):
        rmtree(self.tmpdir)

    @patch('bundlewrap.utils.get')
    def test_download(self, get):
        getresult = MagicMock()
        getresult.iter_content.return_value = ("content", "")
        get.return_value = getresult
        utils.download("url", self.fname)
        self.assertEqual(utils.get_file_contents(self.fname), "content")


class GetAttrFromFileTest(TestCase):
    """
    Tests bundlewrap.utils.getattr_from_file and .get_all_attrs_from_file.
    """
    def setUp(self):
        self.tmpdir = mkdtemp()
        self.fname = join(self.tmpdir, "test.py")

    def tearDown(self):
        rmtree(self.tmpdir)

    @patch('bundlewrap.utils.get_file_contents', return_value="c = 47")
    def test_cache_enabled(self, *args):
        utils.getattr_from_file(self.fname, 'c')
        utils.getattr_from_file(self.fname, 'c')
        utils.get_file_contents.assert_called_once_with(self.fname)

    @patch('bundlewrap.utils.get_file_contents', return_value="c = 47")
    def test_cache_disabled(self, *args):
        utils.getattr_from_file(self.fname, 'c', cache=False)
        utils.getattr_from_file(self.fname, 'c')
        self.assertEqual(utils.get_file_contents.call_count, 2)

    @patch('bundlewrap.utils.get_file_contents', return_value="c = 47")
    def test_cache_ignore(self, *args):
        self.assertEqual(
            utils.getattr_from_file(self.fname, 'c'),
            47,
        )
        utils.get_file_contents.return_value = "c = 48"
        self.assertEqual(
            utils.getattr_from_file(self.fname, 'c', cache=False),
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
            utils.getattr_from_file(self.fname, 'c', cache=False),
            47,
        )
        return
        with open(join(self.tmpdir, self.fname), 'w') as f:
            f.write("c = 48")
        self.assertEqual(
            utils.getattr_from_file(self.fname, 'c'), 48)


class MergeDictTest(TestCase):
    """
    Tests bundlewrap.utils.merge_dict.
    """
    def test_empty_base(self):
        self.assertEqual(
            utils.merge_dict({}, {1: 2}),
            {1: 2},
        )

    def test_empty_update(self):
        self.assertEqual(
            utils.merge_dict({1: 2}, {}),
            {1: 2},
        )

    def test_nested_update(self):
        self.assertEqual(
            utils.merge_dict({1: 2}, {3: {4: 5}}),
            {1: 2, 3: {4: 5}},
        )

    def test_nested_overwrite(self):
        self.assertEqual(
            utils.merge_dict({1: 2}, {1: {3: 4}}),
            {1: {3: 4}},
        )

    def test_nested_two_levels(self):
        self.assertEqual(
            utils.merge_dict({1: {2: 3, 4: 5}}, {1: {2: 6}}),
            {1: {2: 6, 4: 5}},
        )

    def test_overwrite_dict(self):
        self.assertEqual(
            utils.merge_dict({1: {2: 3}}, {1: None}),
            {1: None},
        )

    def test_list_extend(self):
        self.assertEqual(
            utils.merge_dict({1: ["a"]}, {1: ["b"]}),
            {1: ["a", "b"]},
        )

    def test_list_overwrite(self):
        self.assertEqual(
            utils.merge_dict({1: ["a"]}, {1: utils._AtomicList(["b"])}),
            {1: ["b"]},
        )

    def test_set_extend(self):
        self.assertEqual(
            utils.merge_dict({1: set(["a"])}, {1: set(["b"])}),
            {1: set(["a", "b"])},
        )

    def test_tuple_extend(self):
        self.assertEqual(
            utils.merge_dict({1: ("a",)}, {1: ("b",)}),
            {1: ("a", "b")},
        )


class NamesTest(TestCase):
    """
    Tests bundlewrap.utils.names.
    """
    def test_names(self):
        class TestObj(object):
            def __init__(self, name):
                self.name = name

        l = (TestObj("obj1"), TestObj("obj2"))
        self.assertEqual(list(utils.names(l)), ["obj1", "obj2"])
