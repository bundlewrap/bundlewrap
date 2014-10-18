from unittest import TestCase

from mock import MagicMock

from bundlewrap.cmdline import nodes


class NodesTest(TestCase):
    """
    Tests bundlewrap.cmdline.nodes.bw_nodes.
    """
    def setUp(self):
        self.repo = MagicMock()

        bundle1 = MagicMock()
        bundle1.name = "bundle1"
        bundle2 = MagicMock()
        bundle2.name = "bundle2"

        group1 = MagicMock()
        group1.name = "group1"
        group2 = MagicMock()
        group2.name = "group2"

        node1 = MagicMock()
        node1.name = "node1"
        node1.hostname = "node1.example.com"
        node1.bundles = [bundle1, bundle2]
        node1.groups = [group1, group2]

        node2 = MagicMock()
        node2.name = "node2"
        node2.hostname = "node2.example.com"
        node2.bundles = [bundle2]
        node2.groups = [group2]

        node3 = MagicMock()
        node3.name = "node3"
        node3.hostname = "node3.example.com"
        node3.bundles = []
        node3.groups = []

        self.repo.nodes = [node1, node2, node3]
        group2.nodes = [node1, node2]
        self.repo.get_group.return_value = group2

    def test_simple_node_list(self):
        args = {}
        args['filter_group'] = None
        args['show_bundles'] = False
        args['show_hostnames'] = False
        args['show_groups'] = False
        output = list(nodes.bw_nodes(self.repo, args))
        self.assertEqual(
            output,
            ["node1", "node2", "node3"],
        )

    def test_hostname_list(self):
        args = {}
        args['filter_group'] = None
        args['show_bundles'] = False
        args['show_hostnames'] = True
        args['show_groups'] = False
        output = list(nodes.bw_nodes(self.repo, args))
        self.assertEqual(
            output,
            ["node1.example.com", "node2.example.com", "node3.example.com"],
        )

    def test_bundles_list(self):
        args = {}
        args['filter_group'] = None
        args['show_bundles'] = True
        args['show_hostnames'] = False
        args['show_groups'] = False
        output = list(nodes.bw_nodes(self.repo, args))
        self.assertEqual(
            output,
            [
                "node1: bundle1, bundle2",
                "node2: bundle2",
                "node3: ",
            ],
        )

    def test_groups_list(self):
        args = {}
        args['filter_group'] = None
        args['show_bundles'] = False
        args['show_hostnames'] = False
        args['show_groups'] = True
        output = list(nodes.bw_nodes(self.repo, args))
        self.assertEqual(
            output,
            [
                "node1: group1, group2",
                "node2: group2",
                "node3: ",
            ],
        )

    def test_group_filter(self):
        args = {}
        args['filter_group'] = "group2"
        args['show_bundles'] = False
        args['show_hostnames'] = False
        args['show_groups'] = False
        output = list(nodes.bw_nodes(self.repo, args))
        self.assertEqual(
            output,
            [
                "node1",
                "node2",
            ],
        )
