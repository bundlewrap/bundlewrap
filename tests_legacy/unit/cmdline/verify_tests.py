# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from unittest import TestCase

try:
    from unittest.mock import MagicMock
except ImportError:
    from mock import MagicMock

from bundlewrap.cmdline import verify


class FakeNode(object):
    name = "nodename"

    def verify(self, workers=4):
        return ()


class SummaryTest(TestCase):
    """
    Tests bundlewrap.cmdline.verify.stats_summary.
    """
    def test_single_node(self):
        self.assertEqual(
            list(verify.stats_summary({'node1': {'good': 5, 'bad': 3}})),
            ["node health:  62.5%  (5/8 OK)"],
        )

    def test_multiple_nodes(self):
        self.assertEqual(
            list(verify.stats_summary({
                'node1': {'good': 5, 'bad': 3},
                'node2': {'good': 0, 'bad': 0},
                'node3': {'good': 0, 'bad': 3},
                'node4': {'good': 5, 'bad': 0},
            })),
            [
                "node health:",
                "  100.0%  node4  (5/5 OK)",
                "   62.5%  node1  (5/8 OK)",
                "    0.0%  node3  (0/3 OK)",
                "    0.0%  node2  (0/0 OK)",
                "overall:  62.5%  (10/16 OK)",
            ],
        )

    def test_multiple_nodes_all_empty(self):
        self.assertEqual(
            list(verify.stats_summary({
                'node1': {'good': 0, 'bad': 0},
                'node2': {'good': 0, 'bad': 0},
            })),
            [
                "node health:",
                "    0.0%  node2  (0/0 OK)",
                "    0.0%  node1  (0/0 OK)",
                "overall:  0.0%  (0/0 OK)",
            ],
        )


class VerifyTest(TestCase):
    """
    Tests bundlewrap.cmdline.verify.bw_verify.
    """
    def test_interactive(self):
        node1 = FakeNode()
        repo = MagicMock()
        repo.get_node.return_value = node1
        args = {}
        args['item_workers'] = 4
        args['target'] = "node1"
        verify.bw_verify(repo, args)
