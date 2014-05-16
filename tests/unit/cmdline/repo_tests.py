from unittest import TestCase

from mock import MagicMock, patch

from blockwart.cmdline import repo


class DebugTest(TestCase):
    """
    Tests blockwart.cmdline.repo.bw_repo_debug.
    """
    @patch('blockwart.cmdline.repo.interact')
    def test_interactive(self, interact):
        args = MagicMock()
        args.node = None
        repo_obj = MagicMock()
        repo_obj.path = "/dev/null"
        repo_obj_validated = MagicMock()
        with patch(
                'blockwart.cmdline.repo.Repository',
                return_value=repo_obj_validated,
        ) as repo_class:
            repo.bw_repo_debug(repo_obj, args)

            repo_class.assert_called_with(repo_obj.path)
            interact.assert_called_with(
                repo.DEBUG_BANNER,
                local={'repo': repo_obj_validated},
            )

    @patch('blockwart.cmdline.repo.interact')
    def test_interactive_node(self, interact):
        args = MagicMock()
        args.node = "node1"
        args.itemid = None
        node = MagicMock()
        node.name = args.node
        repo_obj = MagicMock()
        repo_obj.path = "/dev/null"
        repo_obj_validated = MagicMock()
        repo_obj_validated.get_node = MagicMock(return_value=node)
        with patch(
                'blockwart.cmdline.repo.Repository',
                return_value=repo_obj_validated,
        ):
            repo.bw_repo_debug(repo_obj, args)
            interact.assert_called_with(
                repo.DEBUG_BANNER_NODE,
                local={
                    'node': node,
                    'repo': repo_obj_validated,
                },
            )


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
    Tests blockwart.cmdline.repo.bw_repo_test.
    """
    def test_ok(self):
        node1 = FakeNode()
        repo_obj = MagicMock()
        repo_obj.nodes = (node1,)
        args = MagicMock()
        args.item_workers = 4
        args.node_workers = 1
        args.target = None
        list(repo.bw_repo_test(repo_obj, args))

    @patch('blockwart.cmdline.repo.exit')
    def test_fail(self, exit):
        node1 = FailNode()
        repo_obj = MagicMock()
        repo_obj.get_node.return_value = node1
        args = MagicMock()
        args.item_workers = 4
        args.node_workers = 1
        args.target = "node1"
        list(repo.bw_repo_test(repo_obj, args))
        exit.assert_called_once_with(1)
