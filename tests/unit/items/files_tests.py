from platform import system
from tempfile import mkstemp
from unittest import TestCase

from mock import MagicMock, patch

from blockwart.exceptions import BundleError
from blockwart.items import files
from blockwart.node import Node
from blockwart.operations import RunResult


class FileContentHashTest(TestCase):
    """
    Tests blockwart.items.files.File.content_hash.
    """
    @patch('blockwart.items.files.hash_local_file')
    def test_binary(self, hash_local_file):
        hash_local_file.return_value = "47"
        bundle = MagicMock()
        bundle.bundle_dir = "/b/dir"
        f = files.File(
            bundle,
            "/foo",
            {'content_type': 'binary', 'source': 'foobar'},
        )
        self.assertEqual(f.content_hash, "47")
        hash_local_file.assert_called_once_with("/b/dir/files/foobar")


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


class HashRemoteTest(TestCase):
    """
    Tests blockwart.items.files.hash_remote_file.
    """
    def test_known_hash(self):
        if system() == "Darwin":
            # no 'sha1sum' on Mac OS
            return
        _, filename = mkstemp()
        with open(filename, 'w') as f:
            f.write("47")
        node = Node(MagicMock(), "localhost")
        self.assertEqual(
            files.hash_remote_file(node, filename),
            "827bfc458708f0b442009c9c9836f7e4b65557fb",
        )


class StatTest(TestCase):
    """
    Tests blockwart.items.files.stat.
    """
    def test_long_mode(self):
        node = MagicMock()
        run_result = RunResult()
        run_result.stdout = "user:group:7777"
        node.run.return_value = run_result
        stat_result = files.stat(node, "/dev/null")
        self.assertEqual(stat_result, {
            'owner': "user",
            'group': "group",
            'mode': "7777",
        })

    def test_short_mode(self):
        node = MagicMock()
        run_result = RunResult()
        run_result.stdout = "user:group:666"
        node.run.return_value = run_result
        stat_result = files.stat(node, "/dev/null")
        self.assertEqual(stat_result, {
            'owner': "user",
            'group': "group",
            'mode': "0666",
        })


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
