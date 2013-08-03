from unittest import TestCase

from mock import MagicMock

from blockwart.cmdline.apply import bw_apply
from blockwart.node import ApplyResult


class FakeNode(object):
    name = "nodename"

    def apply(self, interactive=False):
        assert interactive
        return ApplyResult(self, ())


class ApplyTest(TestCase):
    """
    Tests blockwart.cmdline.apply.bw_apply.
    """
    def test_interactive(self):
        node1 = FakeNode()
        repo = MagicMock()
        repo.get_node.return_value = node1
        args = MagicMock()
        args.interactive = True
        args.target = "node1"
        bw_apply(repo, args)
