from tempfile import mkstemp
from unittest import TestCase

from mock import MagicMock, patch

from blockwart.exceptions import BundleError
from blockwart.items import files


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
