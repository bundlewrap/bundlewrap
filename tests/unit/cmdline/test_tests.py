from unittest import TestCase

from mock import MagicMock, patch

from blockwart.cmdline import test


class FakeNode(object):
    name = "nodename"

    def test(self, workers=4):
        return


class FailNode(object):
    name = "nodename"

    def test(self, workers=4):
        raise RuntimeError("I accidentally")


class TestTest(TestCase):
    """
    Tests blockwart.cmdline.test.bw_test.
    """
    def test_ok(self):
        node1 = FakeNode()
        repo_obj = MagicMock()
        repo_obj.nodes = (node1,)
        args = MagicMock()
        args.item_workers = 4
        args.node_workers = 1
        args.target = None
        list(test.bw_test(repo_obj, args))

    @patch('blockwart.cmdline.test.exit')
    def test_fail(self, exit):
        node1 = FailNode()
        repo_obj = MagicMock()
        repo_obj.get_node.return_value = node1
        args = MagicMock()
        args.item_workers = 4
        args.node_workers = 1
        args.target = "node1"
        list(test.bw_test(repo_obj, args))
        exit.assert_called_once_with(1)
