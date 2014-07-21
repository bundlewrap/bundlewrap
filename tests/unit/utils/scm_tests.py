# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from subprocess import CalledProcessError
from unittest import TestCase

from mock import patch

from bundlewrap.utils import scm


class GetBzrRevTest(TestCase):
    """
    Tests bundlewrap.utils.scm.get_bzr_rev.
    """
    @patch('bundlewrap.utils.scm.check_output')
    def test_ok(self, check_output):
        check_output.return_value = "12345\n"
        self.assertEqual(scm.get_bzr_rev(), "12345")

    @patch('bundlewrap.utils.scm.check_output')
    def test_fail(self, check_output):
        check_output.side_effect = CalledProcessError(None, None)
        self.assertEqual(scm.get_bzr_rev(), None)


class GetGitRevTest(TestCase):
    """
    Tests bundlewrap.utils.scm.get_git_rev.
    """
    @patch('bundlewrap.utils.scm.check_output')
    def test_ok(self, check_output):
        check_output.return_value = "abcdefgh\n"
        self.assertEqual(scm.get_git_rev(), "abcdefgh")

    @patch('bundlewrap.utils.scm.check_output')
    def test_fail(self, check_output):
        check_output.side_effect = CalledProcessError(None, None)
        self.assertEqual(scm.get_git_rev(), None)


class GetHgRevTest(TestCase):
    """
    Tests bundlewrap.utils.scm.get_hg_rev.
    """
    @patch('bundlewrap.utils.scm.check_output')
    def test_ok(self, check_output):
        check_output.return_value = "abcdefgh\n"
        self.assertEqual(scm.get_hg_rev(), "abcdefgh")

    @patch('bundlewrap.utils.scm.check_output')
    def test_fail(self, check_output):
        check_output.side_effect = CalledProcessError(None, None)
        self.assertEqual(scm.get_hg_rev(), None)


class GetRevTest(TestCase):
    """
    Tests bundlewrap.utils.scm.get_rev.
    """
    @patch('bundlewrap.utils.scm.check_output')
    def test_ok(self, check_output):
        check_output.return_value = "abcdefgh\n"
        self.assertEqual(scm.get_rev(), "abcdefgh")

    @patch('bundlewrap.utils.scm.check_output')
    def test_none(self, check_output):
        check_output.side_effect = CalledProcessError(None, None)
        self.assertEqual(scm.get_rev(), None)
