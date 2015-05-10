# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from unittest import TestCase

from bundlewrap.cmdline import zen


class ZenTest(TestCase):
    """
    Tests bundlewrap.cmdline.zen.bw_zen.
    """
    def test_zen(self):
        list(zen.bw_zen(None, None))
