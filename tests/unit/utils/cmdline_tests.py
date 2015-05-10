# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from unittest import TestCase

try:
    from unittest.mock import MagicMock
except ImportError:
    from mock import MagicMock

from bundlewrap.exceptions import NoSuchNode, NoSuchGroup, UsageException
from bundlewrap.utils import cmdline


class GetTargetNodesTest(TestCase):
    """
    Tests bundlewrap.utils.cmdline.get_target_nodes.
    """
    def test_mixed(self):
        def get_node(name):
            if int(name[-1]) > 2:
                raise NoSuchNode()
            return "n" + name[-1]

        def get_group(name):
            group = MagicMock()
            group.nodes = ["g" + name[-1]]
            return group

        repo = MagicMock()
        repo.get_group = get_group
        repo.get_node = get_node
        self.assertEqual(
            set(cmdline.get_target_nodes(repo, "node1, node2,group3")),
            set(["n1", "n2", "g3"]),
        )

    def test_order(self):
        repo = MagicMock()
        repo.get_node = lambda n: int(n[-1])
        self.assertEqual(
            cmdline.get_target_nodes(repo, "node2,node1,node3"),
            [1, 2, 3],
        )

    def test_no_such_node(self):
        def get_node(name):
            raise NoSuchNode()

        def get_group(name):
            group = MagicMock()
            group.nodes = ["g" + name[-1]]
            return group

        repo = MagicMock()
        repo.get_group = get_group
        repo.get_node = get_node
        self.assertEqual(
            cmdline.get_target_nodes(repo, "node1"),
            ["g1"],
        )

    def test_no_such_group(self):
        def get_node(name):
            raise NoSuchNode()

        def get_group(name):
            raise NoSuchGroup()

        repo = MagicMock()
        repo.get_group = get_group
        repo.get_node = get_node
        with self.assertRaises(UsageException):
            cmdline.get_target_nodes(repo, "node1")

    def test_bundle(self):
        bundle1 = MagicMock()
        bundle1.name = "goodbundle"
        bundle2 = MagicMock()
        bundle2.name = "badbundle"

        node1 = MagicMock()
        node1.bundles = (bundle1, bundle2)
        node2 = MagicMock()
        node2.bundles = (bundle2,)

        repo = MagicMock()
        repo.nodes = (node1, node2)

        self.assertEqual(
            cmdline.get_target_nodes(repo, "bundle:goodbundle"),
            [node1],
        )

    def test_negated_bundle(self):
        bundle1 = MagicMock()
        bundle1.name = "goodbundle"
        bundle2 = MagicMock()
        bundle2.name = "badbundle"

        node1 = MagicMock()
        node1.bundles = (bundle1,)
        node2 = MagicMock()
        node2.bundles = (bundle2,)

        repo = MagicMock()
        repo.nodes = (node1, node2)

        self.assertEqual(
            cmdline.get_target_nodes(repo, "!bundle:badbundle"),
            [node1],
        )

    def test_negated_group(self):
        group1 = MagicMock()
        group1.name = "goodgroup"
        group2 = MagicMock()
        group2.name = "badgroup"

        node1 = MagicMock()
        node1.groups = (group1,)
        node2 = MagicMock()
        node2.groups = (group2,)

        repo = MagicMock()
        repo.nodes = (node1, node2)

        self.assertEqual(
            cmdline.get_target_nodes(repo, "!group:badgroup"),
            [node1],
        )
