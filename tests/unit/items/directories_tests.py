# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from unittest import TestCase

try:
    from unittest.mock import call, MagicMock, patch
except ImportError:
    from mock import call, MagicMock, patch

from bundlewrap.exceptions import BundleError
from bundlewrap.items import directories, ItemStatus


class DirectoryFixTest(TestCase):
    """
    Tests bundlewrap.items.directories.Directory.fix.
    """
    @patch('bundlewrap.items.directories.Directory._fix_mode')
    @patch('bundlewrap.items.directories.Directory._fix_owner')
    @patch('bundlewrap.items.directories.Directory._fix_type')
    def test_type(self, fix_type, fix_owner, fix_mode):
        f = directories.Directory(MagicMock(), "/", {})
        pinfo = MagicMock()
        pinfo.exists = False
        status = ItemStatus(correct=False, info={
            'path_info': pinfo,
            'needs_fixing': ['type', 'mode', 'owner'],
        })
        f.fix(status)
        fix_type.assert_called_once_with(status)

    @patch('bundlewrap.items.directories.Directory._fix_mode')
    @patch('bundlewrap.items.directories.Directory._fix_owner')
    @patch('bundlewrap.items.directories.Directory._fix_type')
    def test_mode(self, fix_type, fix_owner, fix_mode):
        f = directories.Directory(MagicMock(), "/", {})
        status = ItemStatus(correct=False, info={
            'needs_fixing': ['mode'],
        })
        f.fix(status)
        self.assertFalse(fix_type.called)
        fix_mode.assert_called_once_with(status)
        self.assertFalse(fix_owner.called)

    @patch('bundlewrap.items.directories.Directory._fix_mode')
    @patch('bundlewrap.items.directories.Directory._fix_owner')
    @patch('bundlewrap.items.directories.Directory._fix_type')
    def test_owner(self, fix_type, fix_owner, fix_mode):
        f = directories.Directory(MagicMock(), "/", {})
        status = ItemStatus(correct=False, info={
            'needs_fixing': ['owner'],
        })
        f.fix(status)
        self.assertFalse(fix_type.called)
        fix_owner.assert_called_once_with(status)
        self.assertFalse(fix_mode.called)

    @patch('bundlewrap.items.directories.Directory._fix_mode')
    @patch('bundlewrap.items.directories.Directory._fix_owner')
    @patch('bundlewrap.items.directories.Directory._fix_type')
    def test_combined(self, fix_type, fix_owner, fix_mode):
        f = directories.Directory(MagicMock(), "/", {})
        status = ItemStatus(correct=False, info={
            'needs_fixing': ['owner', 'mode'],
        })
        f.fix(status)
        self.assertFalse(fix_type.called)
        fix_owner.assert_called_once_with(status)
        fix_mode.assert_called_once_with(status)


class DirectoryFixModeTest(TestCase):
    """
    Tests bundlewrap.items.directories.Directory._fix_mode.
    """
    def test_chmod(self):
        node = MagicMock()
        bundle = MagicMock()
        bundle.node = node
        f = directories.Directory(
            bundle,
            "/foo",
            {'mode': "1234"},
        )
        f._fix_mode(MagicMock())
        node.run.assert_called_once_with("chmod 1234 -- /foo")


class DirectoryFixOwnerTest(TestCase):
    """
    Tests bundlewrap.items.directories.Directory._fix_owner.
    """
    def test_chmod(self):
        node = MagicMock()
        bundle = MagicMock()
        bundle.node = node
        f = directories.Directory(
            bundle,
            "/foo",
            {'owner': "jcleese", 'group': "mp"},
        )
        f._fix_owner(MagicMock())
        node.run.assert_called_once_with("chown jcleese:mp -- /foo")


class DirectoryFixTypeTest(TestCase):
    """
    Tests bundlewrap.items.directories.Directory._fix_type.
    """
    @patch('bundlewrap.items.directories.Directory._fix_mode')
    @patch('bundlewrap.items.directories.Directory._fix_owner')
    def test_rm(self, fix_mode, fix_owner):
        node = MagicMock()
        bundle = MagicMock()
        bundle.node = node
        f = directories.Directory(
            bundle,
            "/foo",
            {},
        )
        f._fix_type(MagicMock())
        assert call("rm -rf -- /foo") in node.run.call_args_list
        assert call("mkdir -p -- /foo") in node.run.call_args_list
        fix_mode.assert_called_once()
        fix_owner.assert_called_once()


class DirectoryGetAutoDepsTest(TestCase):
    """
    Tests bundlewrap.items.directories.Directory.get_auto_deps.
    """
    def test_file_collision(self):
        item1 = MagicMock()
        item1.ITEM_TYPE_NAME = "file"
        item1.id = "file:/foo/bar/baz"
        item1.name = "/foo/bar/baz"

        d = directories.Directory(MagicMock(), "/foo/bar/baz", {})

        items = [item1, d]

        with self.assertRaises(BundleError):
            d.get_auto_deps(items)

    def test_file_parent(self):
        item1 = MagicMock()
        item1.ITEM_TYPE_NAME = "file"
        item1.id = "file:/foo/bar"
        item1.name = "/foo/bar"

        d = directories.Directory(MagicMock(), "/foo/bar/baz", {})

        items = [item1, d]

        with self.assertRaises(BundleError):
            d.get_auto_deps(items)

    def test_subdir(self):
        item1 = MagicMock()
        item1.ITEM_TYPE_NAME = "directory"
        item1.id = "directory:/foo/bar"
        item1.name = "/foo/bar"
        item2 = MagicMock()
        item2.ITEM_TYPE_NAME = "directory"
        item2.id = "directory:/bar/foo"
        item2.name = "/bar/foo"
        item3 = MagicMock()
        item3.ITEM_TYPE_NAME = "file"
        item3.id = "file:/foo/baz"
        item3.name = "/foo/baz"

        d = directories.Directory(MagicMock(), "/foo/bar/baz", {})

        items = [item1, item2, item3, d]

        self.assertEqual(d.get_auto_deps(items), ["directory:/foo/bar"])

    def test_symlink(self):
        item1 = MagicMock()
        item1.ITEM_TYPE_NAME = "symlink"
        item1.id = "symlink:/foo/bar"
        item1.name = "/foo/bar"
        item2 = MagicMock()
        item2.ITEM_TYPE_NAME = "directory"
        item2.id = "directory:/bar/foo"
        item2.name = "/bar/foo"
        item3 = MagicMock()
        item3.ITEM_TYPE_NAME = "file"
        item3.id = "file:/foo/baz"
        item3.name = "/foo/baz"

        d = directories.Directory(MagicMock(), "/foo/bar/baz", {})

        items = [item1, item2, item3, d]

        self.assertEqual(d.get_auto_deps(items), ["symlink:/foo/bar"])

    def test_symlink_collision(self):
        item1 = MagicMock()
        item1.ITEM_TYPE_NAME = "symlink"
        item1.id = "symlink:/foo/bar/baz"
        item1.name = "/foo/bar/baz"

        d = directories.Directory(MagicMock(), "/foo/bar/baz", {})

        items = [item1, d]

        with self.assertRaises(BundleError):
            d.get_auto_deps(items)


class DirectoryGetStatusTest(TestCase):
    """
    Tests bundlewrap.items.directories.Directory.get_status.
    """
    @patch('bundlewrap.items.directories.PathInfo')
    def test_mode(self, PathInfo):
        path_info = MagicMock()
        path_info.mode = "0777"
        path_info.owner = "root"
        path_info.group = "root"
        path_info.is_directory = True
        PathInfo.return_value = path_info

        f = directories.Directory(MagicMock(), "/", {
            'mode': "0664",
            'owner': "root",
            'group': "root",
        })
        status = f.get_status()
        self.assertFalse(status.correct)
        self.assertEqual(status.info['needs_fixing'], ['mode'])

    @patch('bundlewrap.items.directories.PathInfo')
    def test_owner(self, PathInfo):
        path_info = MagicMock()
        path_info.mode = "0664"
        path_info.owner = "jdoe"
        path_info.group = "root"
        path_info.is_directory = True
        PathInfo.return_value = path_info

        f = directories.Directory(MagicMock(), "/", {
            'mode': "0664",
            'owner': "root",
            'group': "root",
        })
        status = f.get_status()
        self.assertFalse(status.correct)
        self.assertEqual(status.info['needs_fixing'], ['owner'])

    @patch('bundlewrap.items.directories.PathInfo')
    def test_group(self, PathInfo):
        path_info = MagicMock()
        path_info.mode = "0664"
        path_info.owner = "root"
        path_info.group = "yolocrowd"
        path_info.is_directory = True
        PathInfo.return_value = path_info

        f = directories.Directory(MagicMock(), "/", {
            'mode': "0664",
            'owner': "root",
            'group': "root",
        })
        status = f.get_status()
        self.assertFalse(status.correct)
        self.assertEqual(status.info['needs_fixing'], ['group'])

    @patch('bundlewrap.items.directories.PathInfo')
    def test_type(self, PathInfo):
        path_info = MagicMock()
        path_info.mode = "0664"
        path_info.owner = "root"
        path_info.group = "root"
        path_info.is_directory = False
        PathInfo.return_value = path_info

        f = directories.Directory(MagicMock(), "/", {
            'mode': "0664",
            'owner': "root",
            'group': "root",
        })
        status = f.get_status()
        self.assertFalse(status.correct)
        self.assertEqual(
            set(status.info['needs_fixing']),
            set(['type']),
        )

    @patch('bundlewrap.items.directories.PathInfo')
    def test_ok(self, PathInfo):
        path_info = MagicMock()
        path_info.mode = "0664"
        path_info.owner = "root"
        path_info.group = "root"
        path_info.is_directory = True
        PathInfo.return_value = path_info

        f = directories.Directory(MagicMock(), "/", {
            'mode': "0664",
            'owner': "root",
            'group': "root",
        })
        status = f.get_status()
        self.assertTrue(status.correct)
        self.assertEqual(status.info['needs_fixing'], [])


class ValidatorModeTest(TestCase):
    """
    Tests bundlewrap.items.directories.validator_mode.
    """
    def test_nondigit(self):
        with self.assertRaises(BundleError):
            directories.validator_mode("my:item", "ohai")

    def test_too_long(self):
        with self.assertRaises(BundleError):
            directories.validator_mode("my:item", "31337")

    def test_too_short(self):
        with self.assertRaises(BundleError):
            directories.validator_mode("my:item", "47")

    def test_invalid_digits(self):
        with self.assertRaises(BundleError):
            directories.validator_mode("my:item", "4748")

    def test_ok(self):
        directories.validator_mode("my:item", "0664")

    def test_ok_short(self):
        directories.validator_mode("my:item", "777")
