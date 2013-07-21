from unittest import TestCase

from blockwart.utils import text


class NameValidationTest(TestCase):
    """
    Tests blockwart.utils.text.validate_name.
    """
    def test_good_names(self):
        for name in (
            "foo",
            "foo-bar2",
            "foo_bar",
            "foo.bar",
            "foo...",
        ):
            self.assertTrue(text.validate_name(name))

    def test_bad_names(self):
        for name in (
            ".foo",
            "foo!bar",
            "foo,bar",
            "foo;bar",
        ):
            self.assertFalse(text.validate_name(name))
