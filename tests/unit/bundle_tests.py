from unittest import TestCase

from mock import MagicMock, patch

from blockwart.bundle import Bundle
from blockwart.exceptions import RepositoryError


class InitTest(TestCase):
    """
    Tests initialization of blockwart.bundle.Bundle.
    """
    @patch('blockwart.bundle.Bundle.validate_name', return_value=False)
    def test_bad_bundle_name(self, *args):
        with self.assertRaises(RepositoryError):
            Bundle(MagicMock(), ".name")


class NameValidationTest(TestCase):
    """
    Tests blockwart.bundle.Bundle.validate_name.
    """
    def test_good_names(self):
        for name in (
            "foo",
            "foo-bar2",
            "foo_bar",
            "foo.bar",
            "foo...",
        ):
            self.assertTrue(Bundle.validate_name(name))

    def test_bad_names(self):
        for name in (
            ".foo",
            "foo!bar",
            "foo,bar",
            "foo;bar",
        ):
            self.assertFalse(Bundle.validate_name(name))
