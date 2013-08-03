from os import makedirs
from os.path import join
from tempfile import mkdtemp, mkstemp
from unittest import TestCase

from mock import call, MagicMock, patch

from blockwart.exceptions import BundleError
from blockwart.items import files, ItemStatus
from blockwart.utils.text import green, red


class ContentProcessorMakoTest(TestCase):
    """
    Tests blockwart.items.files.content_processor_mako.
    """
    def test_template(self):
        item = MagicMock()
        item.node.name = "localhost"
        item.item_dir = mkdtemp()
        makedirs(join(item.item_dir, "a/b"))
        item.attributes = {'source': "a/b/c"}
        with open(join(item.item_dir, "a/b/c"), 'w') as f:
            f.write("Hi from ${node.name}!")
        self.assertEqual(
            files.content_processor_mako(item),
            "Hi from localhost!",
        )


class DiffTest(TestCase):
    """
    Tests blockwart.items.files.diff.
    """
    def test_diff(self):
        content_old = (
            "line1\n"
            "line2\n"
        )
        content_new = (
            "line1\n"
            "line3\n"
        )
        self.assertEqual(
            files.diff(content_old, content_new, "/foo"),
            (
                red("--- /foo") + "\n" +
                green("+++ <blockwart content>") + "\n" +
                "@@ -1,2 +1,2 @@\n"
                " line1\n" +
                red("-line2") + "\n" +
                green("+line3") + "\n"
            ),
        )


class FileContentHashTest(TestCase):
    """
    Tests blockwart.items.files.File.content_hash.
    """
    @patch('blockwart.items.files.hash_local_file', return_value="47")
    def test_binary(self, hash_local_file):
        bundle = MagicMock()
        bundle.bundle_dir = "/b/dir"
        f = files.File(
            bundle,
            "/foo",
            {'content_type': 'binary', 'source': 'foobar'},
        )
        self.assertEqual(f.content_hash, "47")
        hash_local_file.assert_called_once_with("/b/dir/files/foobar")


class FileFixTest(TestCase):
    """
    Tests blockwart.items.files.File.fix.
    """
    @patch('blockwart.items.files.File._fix_content')
    @patch('blockwart.items.files.File._fix_mode')
    @patch('blockwart.items.files.File._fix_owner')
    @patch('blockwart.items.files.File._fix_type')
    def test_type(self, fix_type, fix_owner, fix_mode, fix_content):
        f = files.File(MagicMock(), "/", {})
        status = ItemStatus(correct=False, info={
            'needs_fixing': ['type', 'content', 'mode', 'owner'],
        })
        f.fix(status)
        fix_type.assert_called_once_with(status)
        fix_content.assert_called_once_with(status)
        fix_mode.assert_called_once_with(status)
        fix_owner.assert_called_once_with(status)

    @patch('blockwart.items.files.File._fix_content')
    @patch('blockwart.items.files.File._fix_mode')
    @patch('blockwart.items.files.File._fix_owner')
    @patch('blockwart.items.files.File._fix_type')
    def test_content(self, fix_type, fix_owner, fix_mode, fix_content):
        f = files.File(MagicMock(), "/", {})
        status = ItemStatus(correct=False, info={
            'needs_fixing': ['content'],
        })
        f.fix(status)
        self.assertFalse(fix_type.called)
        fix_content.assert_called_once_with(status)
        self.assertFalse(fix_mode.called)
        self.assertFalse(fix_owner.called)

    @patch('blockwart.items.files.File._fix_content')
    @patch('blockwart.items.files.File._fix_mode')
    @patch('blockwart.items.files.File._fix_owner')
    @patch('blockwart.items.files.File._fix_type')
    def test_mode(self, fix_type, fix_owner, fix_mode, fix_content):
        f = files.File(MagicMock(), "/", {})
        status = ItemStatus(correct=False, info={
            'needs_fixing': ['mode'],
        })
        f.fix(status)
        self.assertFalse(fix_type.called)
        fix_mode.assert_called_once_with(status)
        self.assertFalse(fix_content.called)
        self.assertFalse(fix_owner.called)

    @patch('blockwart.items.files.File._fix_content')
    @patch('blockwart.items.files.File._fix_mode')
    @patch('blockwart.items.files.File._fix_owner')
    @patch('blockwart.items.files.File._fix_type')
    def test_owner(self, fix_type, fix_owner, fix_mode, fix_content):
        f = files.File(MagicMock(), "/", {})
        status = ItemStatus(correct=False, info={
            'needs_fixing': ['owner'],
        })
        f.fix(status)
        self.assertFalse(fix_type.called)
        fix_owner.assert_called_once_with(status)
        self.assertFalse(fix_content.called)
        self.assertFalse(fix_mode.called)

    @patch('blockwart.items.files.File._fix_content')
    @patch('blockwart.items.files.File._fix_mode')
    @patch('blockwart.items.files.File._fix_owner')
    @patch('blockwart.items.files.File._fix_type')
    def test_combined(self, fix_type, fix_owner, fix_mode, fix_content):
        f = files.File(MagicMock(), "/", {})
        status = ItemStatus(correct=False, info={
            'needs_fixing': ['owner', 'mode'],
        })
        f.fix(status)
        self.assertFalse(fix_type.called)
        fix_owner.assert_called_once_with(status)
        fix_mode.assert_called_once_with(status)
        self.assertFalse(fix_content.called)


class FileFixContentTest(TestCase):
    """
    Tests blockwart.items.files.File._fix_content.
    """
    def test_binary(self):
        node = MagicMock()
        bundle = MagicMock()
        bundle.bundle_dir = "/b/dir"
        bundle.node = node
        f = files.File(
            bundle,
            "/foo",
            {'content_type': 'binary', 'source': 'foobar'},
        )
        f._fix_content(MagicMock())
        node.upload.assert_called_once_with("/b/dir/files/foobar", "/foo")

    @patch('blockwart.items.files.File.content', new="47")
    def test_regular(self):
        node = MagicMock()
        bundle = MagicMock()
        bundle.bundle_dir = "/b/dir"
        bundle.node = node
        f = files.File(
            bundle,
            "/foo",
            {'content_type': 'mako'},
        )
        f._fix_content(MagicMock())
        node.upload.assert_called_once()


class FileFixModeTest(TestCase):
    """
    Tests blockwart.items.files.File._fix_mode.
    """
    def test_chmod(self):
        node = MagicMock()
        bundle = MagicMock()
        bundle.node = node
        f = files.File(
            bundle,
            "/foo",
            {'mode': "1234"},
        )
        f._fix_mode(MagicMock())
        node.run.assert_called_once_with("chmod 1234 /foo")


class FileFixOwnerTest(TestCase):
    """
    Tests blockwart.items.files.File._fix_owner.
    """
    def test_chmod(self):
        node = MagicMock()
        bundle = MagicMock()
        bundle.node = node
        f = files.File(
            bundle,
            "/foo",
            {'owner': "jcleese", 'group': "mp"},
        )
        f._fix_owner(MagicMock())
        node.run.assert_called_once_with("chown jcleese:mp /foo")


class FileFixTypeTest(TestCase):
    """
    Tests blockwart.items.files.File._fix_type.
    """
    def test_rm(self):
        node = MagicMock()
        bundle = MagicMock()
        bundle.node = node
        f = files.File(
            bundle,
            "/foo",
            {},
        )
        f._fix_type(MagicMock())
        self.assertEqual(
            node.run.call_args_list,
            [call("rm -rf /foo"), call("mkdir -p /")],
        )


class FileGetStatusTest(TestCase):
    """
    Tests blockwart.items.files.File.get_status.
    """
    @patch('blockwart.items.files.File.content_hash', new="47")
    @patch('blockwart.items.files.PathInfo')
    def test_mode(self, PathInfo):
        path_info = MagicMock()
        path_info.mode = "0777"
        path_info.owner = "root"
        path_info.group = "root"
        path_info.sha1 = "47"
        path_info.is_file = True
        PathInfo.return_value = path_info

        f = files.File(MagicMock(), "/", {
            'mode': "0664",
            'owner': "root",
            'group': "root",
        })
        status = f.get_status()
        self.assertFalse(status.correct)
        self.assertEqual(status.info['needs_fixing'], ['mode'])

    @patch('blockwart.items.files.File.content_hash', new="47")
    @patch('blockwart.items.files.PathInfo')
    def test_owner(self, PathInfo):
        path_info = MagicMock()
        path_info.mode = "0664"
        path_info.owner = "jdoe"
        path_info.group = "root"
        path_info.sha1 = "47"
        path_info.is_file = True
        PathInfo.return_value = path_info

        f = files.File(MagicMock(), "/", {
            'mode': "0664",
            'owner': "root",
            'group': "root",
        })
        status = f.get_status()
        self.assertFalse(status.correct)
        self.assertEqual(status.info['needs_fixing'], ['owner'])

    @patch('blockwart.items.files.File.content_hash', new="47")
    @patch('blockwart.items.files.PathInfo')
    def test_group(self, PathInfo):
        path_info = MagicMock()
        path_info.mode = "0664"
        path_info.owner = "root"
        path_info.group = "yolocrowd"
        path_info.sha1 = "47"
        path_info.is_file = True
        PathInfo.return_value = path_info

        f = files.File(MagicMock(), "/", {
            'mode': "0664",
            'owner': "root",
            'group': "root",
        })
        status = f.get_status()
        self.assertFalse(status.correct)
        self.assertEqual(status.info['needs_fixing'], ['owner'])

    @patch('blockwart.items.files.File.content_hash', new="47")
    @patch('blockwart.items.files.PathInfo')
    def test_content(self, PathInfo):
        path_info = MagicMock()
        path_info.mode = "0664"
        path_info.owner = "root"
        path_info.group = "root"
        path_info.sha1 = "48"
        path_info.is_file = True
        PathInfo.return_value = path_info

        f = files.File(MagicMock(), "/", {
            'mode': "0664",
            'owner': "root",
            'group': "root",
        })
        status = f.get_status()
        self.assertFalse(status.correct)
        self.assertEqual(
            set(status.info['needs_fixing']),
            set(['content', 'mode', 'owner']),
        )

    @patch('blockwart.items.files.File.content_hash', new="47")
    @patch('blockwart.items.files.PathInfo')
    def test_type(self, PathInfo):
        path_info = MagicMock()
        path_info.mode = "0664"
        path_info.owner = "root"
        path_info.group = "root"
        path_info.sha1 = "47"
        path_info.is_file = False
        PathInfo.return_value = path_info

        f = files.File(MagicMock(), "/", {
            'mode': "0664",
            'owner': "root",
            'group': "root",
        })
        status = f.get_status()
        self.assertFalse(status.correct)
        self.assertEqual(
            set(status.info['needs_fixing']),
            set(['type', 'content', 'mode', 'owner']),
        )

    @patch('blockwart.items.files.File.content_hash', new="47")
    @patch('blockwart.items.files.PathInfo')
    def test_ok(self, PathInfo):
        path_info = MagicMock()
        path_info.mode = "0664"
        path_info.owner = "root"
        path_info.group = "root"
        path_info.sha1 = "47"
        path_info.is_file = True
        PathInfo.return_value = path_info

        f = files.File(MagicMock(), "/", {
            'mode': "0664",
            'owner': "root",
            'group': "root",
        })
        status = f.get_status()
        self.assertTrue(status.correct)
        self.assertEqual(status.info['needs_fixing'], [])


class HashLocalTest(TestCase):
    """
    Tests blockwart.items.files.hash_local_file.
    """
    def test_known_hash(self):
        _, filename = mkstemp()
        with open(filename, 'w') as f:
            f.write("47")
        self.assertEqual(
            files.hash_local_file(filename),
            "827bfc458708f0b442009c9c9836f7e4b65557fb",
        )


class ValidatorModeTest(TestCase):
    """
    Tests blockwart.items.files.validator_mode.
    """
    def test_nondigit(self):
        with self.assertRaises(BundleError):
            files.validator_mode("my:item", "ohai")

    def test_too_long(self):
        with self.assertRaises(BundleError):
            files.validator_mode("my:item", "31337")

    def test_too_short(self):
        with self.assertRaises(BundleError):
            files.validator_mode("my:item", "47")

    def test_invalid_digits(self):
        with self.assertRaises(BundleError):
            files.validator_mode("my:item", "4748")

    def test_ok(self):
        files.validator_mode("my:item", "0664")

    def test_ok_short(self):
        files.validator_mode("my:item", "777")


class ValidateAttributesTest(TestCase):
    """
    Tests blockwart.items.files.File.validate_attributes.
    """
    def test_validator_call(self):
        validator = MagicMock()
        attr_val = {
            'attr1': validator,
            'attr2': validator,
        }
        with patch('blockwart.items.files.ATTRIBUTE_VALIDATORS', new=attr_val):
            f = files.File(MagicMock(), "test", {}, skip_validation=True)
            f.validate_attributes({'attr1': 1, 'attr2': 2})
        validator.assert_any_call(f.id, 1)
        validator.assert_any_call(f.id, 2)
        self.assertEqual(validator.call_count, 2)
