from unittest import TestCase

from bundlewrap.utils import text


class IsSubdirectoryTest(TestCase):
    """
    Tests bundlewrap.utils.text.is_subdirectory.
    """
    def test_simple_subdir(self):
        self.assertTrue(text.is_subdirectory("/foo/bar", "/foo/bar/baz"))

    def test_simple_nosubdir(self):
        self.assertFalse(text.is_subdirectory("/foo/bar", "/foo/baz/baz"))

    def test_simple_substr(self):
        self.assertFalse(text.is_subdirectory("/foo/bar", "/foo/barbaz"))

    def test_root(self):
        self.assertTrue(text.is_subdirectory("/", "/foo"))

    def test_identical(self):
        self.assertFalse(text.is_subdirectory("/foo", "/foo"))

    def test_slash(self):
        self.assertFalse(text.is_subdirectory("/foo", "/foo\/bar"))

    def test_relative(self):
        with self.assertRaises(ValueError):
            text.is_subdirectory("/foo", "bar")


class NameValidationTest(TestCase):
    """
    Tests bundlewrap.utils.text.validate_name.
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
