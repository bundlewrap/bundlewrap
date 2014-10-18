from unittest import TestCase

from mock import MagicMock, patch

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
    @patch('bundlewrap.cmdline.test.PluginManager')
    def test_ok(self, PluginManager):
        node1 = FakeNode()
        repo_obj = MagicMock()
        repo_obj.nodes = (node1,)
        repo_obj.path = "/dev/null"
        args = {}
        args['item_workers'] = 4
        args['node_workers'] = 1
        args['plugin_conflict_error'] = True
        args['target'] = None
        pm = MagicMock()
        pm.list.return_value = (
            ("foo", 1),
        )
        pm.local_modifications.return_value = ()
        PluginManager.return_value = pm
        list(test.bw_test(repo_obj, args))

    def test_fail(self):
        node1 = FailNode()
        repo_obj = MagicMock()
        repo_obj.get_node.return_value = node1
        args = {}
        args['item_workers'] = 4
        args['node_workers'] = 1
        args['plugin_conflict_error'] = False
        args['target'] = "node1"
        self.assertEqual(list(test.bw_test(repo_obj, args))[-1], 1)

    @patch('bundlewrap.cmdline.test.PluginManager')
    def test_plugin_conflict(self, PluginManager):
        node1 = FakeNode()
        repo_obj = MagicMock()
        repo_obj.get_node.return_value = node1
        args = {}
        args['item_workers'] = 4
        args['node_workers'] = 1
        args['plugin_conflict_error'] = True
        args['target'] = "node1"
        pm = MagicMock()
        pm.list.return_value = (
            ("foo", 1),
        )
        pm.local_modifications.return_value = (
            ("/foo.py", "23", "47"),
        )
        PluginManager.return_value = pm
        self.assertEqual(list(test.bw_test(repo_obj, args))[-1], 1)
