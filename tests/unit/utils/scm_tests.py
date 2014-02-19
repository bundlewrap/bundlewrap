# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from subprocess import CalledProcessError
from unittest import TestCase

from mock import patch

from blockwart.utils import scm


class GetRevTest(TestCase):
    """
    Tests blockwart.utils.scm.get_rev.
    """
    @patch('blockwart.utils.scm.check_output')
    def test_git(self, check_output):
        check_output.return_value = "abcdefgh\n"
        self.assertEqual(scm.get_rev(), "abcdefgh")

    @patch('blockwart.utils.scm.check_output')
    def test_none(self, check_output):
        check_output.side_effect = CalledProcessError(None, None)
        self.assertEqual(scm.get_rev(), None)
