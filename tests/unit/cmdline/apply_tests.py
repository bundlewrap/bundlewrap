from unittest import TestCase

from mock import MagicMock, patch

from blockwart.cmdline.apply import _get_target_list, bw_apply
from blockwart.exceptions import UsageException
from blockwart.node import ApplyResult, Node


class FakeNode(object):
    name = "nodename"

    def apply(self, interactive=False):
        assert interactive
        return ApplyResult(self, ())


class ApplyTest(TestCase):
    """
    Tests blockwart.cmdline.apply.bw_apply.
    """
    @patch('blockwart.cmdline.apply._get_target_list')
    def test_interactive(self, _get_target_list):
        node1 = FakeNode()
        node2 = FakeNode()
        _get_target_list.return_value = [node1, node2]
        args = MagicMock()
        args.interactive = True
        bw_apply(MagicMock(), args)


class GetTargetListTest(TestCase):
    """
    Tests blockwart.cmdline.apply._get_target_list.
    """
    def test_no_nodes_or_groups(self):
        with self.assertRaises(UsageException):
            _get_target_list(MagicMock(), None, None)

    def test_single_node(self):
        node1 = Node(None, "node1", {})
        repo = MagicMock()
        repo.get_node = MagicMock(return_value=node1)
        target_nodes = _get_target_list(repo, None, "node1")
        self.assertEqual(target_nodes, [node1])
        repo.get_node.assert_called_once_with("node1")

    def test_single_group(self):
        node1 = Node(None, "node1", {})
        node2 = Node(None, "node2", {})
        group = MagicMock()
        group.nodes = (node1, node2)
        repo = MagicMock()
        repo.get_group = MagicMock(return_value=group)
        target_nodes = _get_target_list(repo, "group1", None)
        self.assertEqual(target_nodes, [node1, node2])

    def test_multiple(self):
        node1 = Node(None, "node1", {})
        node2 = Node(None, "node2", {})
        node3 = Node(None, "node3", {})
        group1 = MagicMock()
        group1.nodes = (node1, node2)
        group2 = MagicMock()
        group2.nodes = (node2, node3)
        groups = [group1, group2]
        nodes = [node1, node2]
        repo = MagicMock()
        repo.get_group = MagicMock(side_effect=lambda n: groups.pop(0))
        repo.get_node = MagicMock(side_effect=lambda n: nodes.pop(0))
        target_nodes = _get_target_list(repo, "group1,group2", "node1,node2")
        self.assertEqual(target_nodes, [node1, node2, node3])
