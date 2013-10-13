from unittest import TestCase

from mock import call, MagicMock, patch

from blockwart.items import symlinks, ItemStatus


class SymlinkFixTest(TestCase):
    """
    Tests blockwart.items.symlinks.Symlink.fix.
    """
    @patch('blockwart.items.symlinks.Symlink._fix_owner')
    @patch('blockwart.items.symlinks.Symlink._fix_type')
    def test_type(self, fix_type, fix_owner):
        f = symlinks.Symlink(MagicMock(), "/", {'target': "/bar"})
        status = ItemStatus(correct=False, info={
            'needs_fixing': ['type', 'owner'],
        })
        f.fix(status)
        fix_type.assert_called_once_with(status)

    @patch('blockwart.items.symlinks.Symlink._fix_owner')
    @patch('blockwart.items.symlinks.Symlink._fix_type')
    def test_owner(self, fix_type, fix_owner):
        f = symlinks.Symlink(MagicMock(), "/", {'target': "/bar"})
        status = ItemStatus(correct=False, info={
            'needs_fixing': ['owner'],
        })
        f.fix(status)
        self.assertFalse(fix_type.called)
        fix_owner.assert_called_once_with(status)


class SymlinkFixOwnerTest(TestCase):
    """
    Tests blockwart.items.symlinks.Symlink._fix_owner.
    """
    def test_chmod(self):
        node = MagicMock()
        bundle = MagicMock()
        bundle.node = node
        f = symlinks.Symlink(
            bundle,
            "/foo",
            {'owner': "jcleese", 'group': "mp", 'target': "/bar"},
        )
        f._fix_owner(MagicMock())
        node.run.assert_called_once_with("chown -h jcleese:mp /foo")


class SymlinkFixTypeTest(TestCase):
    """
    Tests blockwart.items.symlinks.Symlink._fix_type.
    """
    @patch('blockwart.items.symlinks.Symlink._fix_owner')
    def test_rm(self, fix_owner):
        node = MagicMock()
        bundle = MagicMock()
        bundle.node = node
        f = symlinks.Symlink(
            bundle,
            "/foo",
            {'target': "/bar"},
        )
        f._fix_type(MagicMock())
        assert call("rm -rf /foo") in node.run.call_args_list
        assert call("ln -s /bar /foo") in node.run.call_args_list
        fix_owner.assert_called_once()


class SymlinkGetStatusTest(TestCase):
    """
    Tests blockwart.items.symlinks.Symlink.get_status.
    """
    @patch('blockwart.items.symlinks.PathInfo')
    def test_owner(self, PathInfo):
        path_info = MagicMock()
        path_info.mode = "0777"
        path_info.owner = "jdoe"
        path_info.group = "root"
        path_info.is_symlink = True
        PathInfo.return_value = path_info

        f = symlinks.Symlink(MagicMock(), "/", {
            'owner': "root",
            'group': "root",
            'target': "/bar",
        })
        status = f.get_status()
        self.assertFalse(status.correct)
        self.assertEqual(status.info['needs_fixing'], ['owner'])

    @patch('blockwart.items.symlinks.PathInfo')
    def test_group(self, PathInfo):
        path_info = MagicMock()
        path_info.mode = "0777"
        path_info.owner = "root"
        path_info.group = "yolocrowd"
        path_info.is_symlink = True
        PathInfo.return_value = path_info

        f = symlinks.Symlink(MagicMock(), "/", {
            'owner': "root",
            'group': "root",
            'target': "/bar",
        })
        status = f.get_status()
        self.assertFalse(status.correct)
        self.assertEqual(status.info['needs_fixing'], ['group'])

    @patch('blockwart.items.symlinks.PathInfo')
    def test_type(self, PathInfo):
        path_info = MagicMock()
        path_info.mode = "0777"
        path_info.owner = "root"
        path_info.group = "root"
        path_info.is_symlink = False
        PathInfo.return_value = path_info

        f = symlinks.Symlink(MagicMock(), "/", {
            'owner': "root",
            'group': "root",
            'target': "/bar",
        })
        status = f.get_status()
        self.assertFalse(status.correct)
        self.assertEqual(
            set(status.info['needs_fixing']),
            set(['type']),
        )

    @patch('blockwart.items.symlinks.PathInfo')
    def test_ok(self, PathInfo):
        path_info = MagicMock()
        path_info.mode = "0777"
        path_info.owner = "root"
        path_info.group = "root"
        path_info.is_symlink = True
        PathInfo.return_value = path_info

        f = symlinks.Symlink(MagicMock(), "/", {
            'owner': "root",
            'group': "root",
            'target': "/bar",
        })
        status = f.get_status()
        self.assertTrue(status.correct)
        self.assertEqual(status.info['needs_fixing'], [])


class ValidateAttributesTest(TestCase):
    """
    Tests blockwart.items.symlinks.Symlink.validate_attributes.
    """
    def test_validator_call(self):
        validator = MagicMock()
        attr_val = {
            'attr1': validator,
            'attr2': validator,
        }
        with patch('blockwart.items.symlinks.ATTRIBUTE_VALIDATORS', new=attr_val):
            f = symlinks.Symlink(MagicMock(), "test", {'target': "/bar"},
                                 skip_validation=True)
            f.validate_attributes({'attr1': 1, 'attr2': 2})
        validator.assert_any_call(f.id, 1)
        validator.assert_any_call(f.id, 2)
        self.assertEqual(validator.call_count, 2)
