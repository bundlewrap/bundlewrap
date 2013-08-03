from unittest import TestCase

from mock import MagicMock

from blockwart.exceptions import NoSuchNode, NoSuchGroup, UsageException
from blockwart.utils import cmdline


class GetTargetNodesTest(TestCase):
    """
    Tests blockwart.utils.cmdline.get_target_nodes.
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
