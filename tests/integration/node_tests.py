# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from unittest import TestCase

from bundlewrap.node import Node


class NodeTest(TestCase):
    def test_run_stdout(self):
        n = Node('localhost', {})
        r = n.run("echo -n 47")
        self.assertEqual(r.stdout, "47")
