from os.path import exists, join
from shutil import rmtree
from tempfile import mkdtemp
from unittest import TestCase

from mock import MagicMock

from bundlewrap.cmdline import items


class MockItem(object):
    def __init__(self, id):
        self.content = "content"
        self.id = id
        self.name = id.split(":")[1]

    def __str__(self):
        return self.id


class ItemsTest(TestCase):
    """
    Tests bundlewrap.cmdline.items.bw_items.
    """
    def setUp(self):
        item1 = MockItem("type1:item1")
        item2 = MockItem("type1:item2")
        item3 = MockItem("directory:/bar/baz")
        item4 = MockItem("file:/foo/47")
        item4.attributes = {'content_type': 'mako'}
        item5 = MockItem("file:/foo/48")
        item5.attributes = {'content_type': 'binary'}

        node = MagicMock()
        node.items = (item1, item2, item3, item4, item5)

        self.repo = MagicMock()
        self.repo.get_node.return_value = node

        self.tmpdir = mkdtemp()
        rmtree(self.tmpdir)

    def tearDown(self):
        try:
            rmtree(self.tmpdir)
        except:
            pass

    def test_simple_item_list(self):
        args = MagicMock()
        args.file_preview_path = None
        args.node = "node1"
        args.show_repr = False

        output = list(items.bw_items(self.repo, args))

        self.assertEqual(
            output,
            [
                "type1:item1",
                "type1:item2",
                "directory:/bar/baz",
                "file:/foo/47",
                "file:/foo/48",
            ],
        )

    def test_file_previews(self):
        args = MagicMock()
        args.file_preview_path = self.tmpdir
        args.node = "node1"
        args.show_repr = False

        list(items.bw_items(self.repo, args))

        self.assertTrue(exists(join(self.tmpdir, "foo/47")))
        self.assertFalse(exists(join(self.tmpdir, "foo/48")))
        with open(join(self.tmpdir, "foo/47")) as f:
            self.assertEqual(f.read(), "content")
