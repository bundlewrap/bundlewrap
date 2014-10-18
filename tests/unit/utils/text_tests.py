# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from unittest import TestCase

from bundlewrap.utils import text


class ForceTextTest(TestCase):
    """
    Tests bundlewrap.utils.text.force_text.
    """
    def test_nontext(self):
        self.assertEqual(text.force_text(None), None)
        self.assertEqual(text.force_text(True), True)
        self.assertEqual(text.force_text(False), False)
        e = Exception()
        self.assertEqual(text.force_text(e), e)
        self.assertEqual(text.force_text({}), {})

    def test_unsupported_encoding(self):
        self.assertEqual(text.force_text(u"ö".encode('latin-1')), u"�")

    def test_unicode(self):
        self.assertEqual(text.force_text(u"ö"), u"ö")

    def test_utf8(self):
        self.assertEqual(text.force_text(b"ö"), u"ö")


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
