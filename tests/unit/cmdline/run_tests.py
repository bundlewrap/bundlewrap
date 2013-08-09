from unittest import TestCase

from mock import MagicMock, patch

from blockwart.cmdline import run
from blockwart.operations import RunResult


class FakeNode(object):
    def __init__(self, nodename):
        self.name = nodename
        self.result = RunResult()
        self.result.stdout = "some\noutput"
        self.result.stderr = "some errors"
        self.result.return_code = 47

    def run(self, *args, **kwargs):
        return self.result


class RunTest(TestCase):
    """
    Tests blockwart.cmdline.run.bw_run.
    """
    @patch('blockwart.cmdline.run.get_target_nodes')
    def test_single_node_fail(self, get_target_nodes):
        args = MagicMock()
        args.command = "foo"
        args.may_fail = False
        args.node_workers = 1
        args.sudo = True
        args.verbose = False

        node = FakeNode("node1")
        get_target_nodes.return_value = [node]

        output = list(run.bw_run(MagicMock(), args))

        self.assertEqual(output[0:3], [
            "node1 (stdout): some",
            "node1 (stdout): output",
            "node1 (stderr): some errors",
        ])
        self.assertTrue(output[3].startswith("node1: failed after "))
        self.assertTrue(output[3].endswith("s (return code 47)"))

    @patch('blockwart.cmdline.run.get_target_nodes')
    def test_group_success(self, get_target_nodes):
        args = MagicMock()
        args.command = "foo"
        args.may_fail = False
        args.node_workers = 2
        args.sudo = True
        args.verbose = False

        node1 = FakeNode("node1")
        node1.result.return_code = 0
        node2 = FakeNode("node2")
        node2.result.return_code = 0
        get_target_nodes.return_value = [node1, node2]

        output = list(run.bw_run(MagicMock(), args))
        self.assertTrue("completed successfully after" in output[0])
        self.assertTrue("completed successfully after" in output[1])
        self.assertEqual(len(output), 2)
