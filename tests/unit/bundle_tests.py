from unittest import TestCase

from blockwart.bundle import Bundle


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
