from unittest import TestCase

from mock import MagicMock

from blockwart.cmdline import run
from blockwart.exceptions import NoSuchNode


class RunTest(TestCase):
    """
    Tests blockwart.cmdline.run.bw_run.
    """
    def test_single_node_fail(self):
        args = MagicMock()
        args.target = "node1"
        args.verbose = False

        node = MagicMock()
        node.name = args.target
        result = MagicMock()
        result.return_code = 47
        result.stdout = "foo \nbar"
        result.stderr = "pebkac\n"
        node.run = MagicMock(return_value=result)

        repo = MagicMock()
        repo.get_node = MagicMock(return_value=node)

        output = list(run.bw_run(repo, args))

        repo.get_node.assert_called_once_with(args.target)
        self.assertTrue(node.run.called)
        self.assertEqual(output[0:3], [
            "node1 (stdout): foo ",
            "node1 (stdout): bar",
            "node1 (stderr): pebkac",
        ])
        self.assertTrue(output[3].startswith("node1: failed after "))
        self.assertTrue(output[3].endswith("s (return code 47)"))

    def test_group_success(self):
        def raise_no_node(*args, **kwargs):
            raise NoSuchNode()

        args = MagicMock()
        args.target = "group1"

        node1 = MagicMock()
        node1.name = "node1"
        result = MagicMock()
        result.return_code = 0
        result.stdout = "47"
        result.stderr = ""
        node1.run = MagicMock(return_value=result)

        node2 = MagicMock()
        node2.name = "node2"
        node2.run = MagicMock(return_value=result)

        group = MagicMock()
        group.nodes = (node1, node2)

        repo = MagicMock()
        repo.get_group = MagicMock(return_value=group)
        repo.get_node = MagicMock(side_effect=raise_no_node)

        output = list(run.bw_run(repo, args))

        repo.get_group.assert_called_once_with(args.target)
        repo.get_node.assert_called_once_with(args.target)

        self.assertTrue(node1.run.called)
        self.assertTrue(node2.run.called)
        self.assertTrue(output[0].startswith("node1: completed successfully after "))
        self.assertTrue(output[1].startswith("node2: completed successfully after "))
