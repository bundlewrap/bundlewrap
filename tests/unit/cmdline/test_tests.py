from unittest import TestCase

from mock import MagicMock

from bundlewrap.cmdline import test


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
    Tests bundlewrap.cmdline.test.bw_test.
    """
    def test_ok(self):
        node1 = FakeNode()
        repo_obj = MagicMock()
        repo_obj.nodes = (node1,)
        repo_obj.path = "/dev/null"
        args = MagicMock()
        args.item_workers = 4
        args.node_workers = 1
        args.plugin_conflict_error = True
        args.target = None
        list(test.bw_test(repo_obj, args))

    def test_fail(self):
        node1 = FailNode()
        repo_obj = MagicMock()
        repo_obj.get_node.return_value = node1
        args = MagicMock()
        args.item_workers = 4
        args.node_workers = 1
        args.plugin_conflict_error = False
        args.target = "node1"
        self.assertEqual(list(test.bw_test(repo_obj, args))[-1], 1)
