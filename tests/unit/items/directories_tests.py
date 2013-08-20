from unittest import TestCase

from mock import call, MagicMock, patch

from blockwart.exceptions import BundleError
from blockwart.items import directories, ItemStatus


class DirectoryFixTest(TestCase):
    """
    Tests blockwart.items.directories.Directory.fix.
    """
    @patch('blockwart.items.directories.Directory._fix_mode')
    @patch('blockwart.items.directories.Directory._fix_owner')
    @patch('blockwart.items.directories.Directory._fix_type')
    def test_type(self, fix_type, fix_owner, fix_mode):
        f = directories.Directory(MagicMock(), "/", {})
        status = ItemStatus(correct=False, info={
            'needs_fixing': ['type', 'mode', 'owner'],
        })
        f.fix(status)
        fix_type.assert_called_once_with(status)

    @patch('blockwart.items.directories.Directory._fix_mode')
    @patch('blockwart.items.directories.Directory._fix_owner')
    @patch('blockwart.items.directories.Directory._fix_type')
    def test_mode(self, fix_type, fix_owner, fix_mode):
        f = directories.Directory(MagicMock(), "/", {})
        status = ItemStatus(correct=False, info={
            'needs_fixing': ['mode'],
        })
        f.fix(status)
        self.assertFalse(fix_type.called)
        fix_mode.assert_called_once_with(status)
        self.assertFalse(fix_owner.called)

    @patch('blockwart.items.directories.Directory._fix_mode')
    @patch('blockwart.items.directories.Directory._fix_owner')
    @patch('blockwart.items.directories.Directory._fix_type')
    def test_owner(self, fix_type, fix_owner, fix_mode):
        f = directories.Directory(MagicMock(), "/", {})
        status = ItemStatus(correct=False, info={
            'needs_fixing': ['owner'],
        })
        f.fix(status)
        self.assertFalse(fix_type.called)
        fix_owner.assert_called_once_with(status)
        self.assertFalse(fix_mode.called)

    @patch('blockwart.items.directories.Directory._fix_mode')
    @patch('blockwart.items.directories.Directory._fix_owner')
    @patch('blockwart.items.directories.Directory._fix_type')
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
    Tests blockwart.items.directories.Directory._fix_mode.
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
        node.run.assert_called_once_with("chmod 1234 /foo")


class DirectoryFixOwnerTest(TestCase):
    """
    Tests blockwart.items.directories.Directory._fix_owner.
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
        node.run.assert_called_once_with("chown jcleese:mp /foo")


class DirectoryFixTypeTest(TestCase):
    """
    Tests blockwart.items.directories.Directory._fix_type.
    """
    @patch('blockwart.items.directories.Directory._fix_mode')
    @patch('blockwart.items.directories.Directory._fix_owner')
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
        assert call("rm -rf /foo") in node.run.call_args_list
        assert call("mkdir -p /foo") in node.run.call_args_list
        fix_mode.assert_called_once()
        fix_owner.assert_called_once()


class DirectoryGetStatusTest(TestCase):
    """
    Tests blockwart.items.directories.Directory.get_status.
    """
    @patch('blockwart.items.directories.PathInfo')
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

    @patch('blockwart.items.directories.PathInfo')
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

    @patch('blockwart.items.directories.PathInfo')
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

    @patch('blockwart.items.directories.PathInfo')
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

    @patch('blockwart.items.directories.PathInfo')
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
    Tests blockwart.items.directories.validator_mode.
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
