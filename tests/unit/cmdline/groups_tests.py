from unittest import TestCase

try:
    from unittest.mock import MagicMock
except ImportError:
    from mock import MagicMock

from bundlewrap.cmdline import groups


class GroupsTest(TestCase):
    """
    Tests bundlewrap.cmdline.groups.bw_groups.
    """
    def setUp(self):
        self.repo = MagicMock()
        node1 = MagicMock()
        node1.name = "node1"
        node2 = MagicMock()
        node2.name = "node2"
        group1 = MagicMock()
        group1.name = "group1"
        group1.nodes = [node1, node2]
        group2 = MagicMock()
        group2.name = "group2"
        group2.nodes = [node1]
        group3 = MagicMock()
        group3.name = "group3"
        group3.nodes = []
        self.repo.groups = [group1, group2, group3]

    def test_simple_group_list(self):
        args = {'show_nodes': False}
        output = list(groups.bw_groups(self.repo, args))
        self.assertEqual(
            output,
            ["group1", "group2", "group3"],
        )

    def test_nodes_list(self):
        args = {'show_nodes': True}
        output = list(groups.bw_groups(self.repo, args))
        self.assertEqual(
            output,
            [
                "group1: node1, node2",
                "group2: node1",
                "group3: ",
            ],
        )
