from unittest import TestCase

from mock import MagicMock

from blockwart.cmdline import nodes


class NodesTest(TestCase):
    """
    Tests blockwart.cmdline.nodes.bw_nodes.
    """
    def setUp(self):
        self.repo = MagicMock()
        group1 = MagicMock()
        group1.name = "group1"
        group2 = MagicMock()
        group2.name = "group2"
        node1 = MagicMock()
        node1.name = "node1"
        node1.hostname = "node1.example.com"
        node1.groups = [group1, group2]
        node2 = MagicMock()
        node2.name = "node2"
        node2.hostname = "node2.example.com"
        node2.groups = [group2]
        node3 = MagicMock()
        node3.name = "node3"
        node3.hostname = "node3.example.com"
        node3.groups = []
        self.repo.nodes = [node1, node2, node3]

    def test_simple_node_list(self):
        args = MagicMock()
        args.show_hostnames = False
        args.show_groups = False
        output = list(nodes.bw_nodes(self.repo, args))
        self.assertEqual(
            output,
            ["node1", "node2", "node3"],
        )

    def test_hostname_list(self):
        args = MagicMock()
        args.show_hostnames = True
        args.show_groups = False
        output = list(nodes.bw_nodes(self.repo, args))
        self.assertEqual(
            output,
            ["node1.example.com", "node2.example.com", "node3.example.com"],
        )

    def test_groups_list(self):
        args = MagicMock()
        args.show_hostnames = False
        args.show_groups = True
        output = list(nodes.bw_nodes(self.repo, args))
        self.assertEqual(
            output,
            [
                "node1: group1, group2",
                "node2: group2",
                "node3: ",
            ],
        )
