from datetime import datetime
from unittest import TestCase

from mock import MagicMock

from blockwart.cmdline.apply import bw_apply, format_node_action_result, \
    format_node_item_result
from blockwart.node import ApplyResult


class FakeNode(object):
    name = "nodename"

    def apply(self, interactive=False, workers=4, force=False):
        assert interactive
        result = ApplyResult(self, ())
        result.start = datetime(2013, 8, 10, 0, 0)
        result.end = datetime(2013, 8, 10, 0, 1)
        return result


class ApplyTest(TestCase):
    """
    Tests blockwart.cmdline.apply.bw_apply.
    """
    def test_interactive(self):
        node1 = FakeNode()
        repo = MagicMock()
        repo.get_node.return_value = node1
        args = MagicMock()
        args.force = False
        args.interactive = True
        args.item_workers = 4
        args.target = "node1"
        output = list(bw_apply(repo, args))
        self.assertTrue(output[0].startswith("\nnodename: run started at "))
        self.assertTrue(output[1].startswith("\n  nodename: run completed after "))
        self.assertEqual(
            output[2],
            "  items: 0 correct, 0 fixed, 0 skipped, 0 unfixable, 0 failed",
        )
        self.assertEqual(
            output[3],
            "  actions: 0 ok, 0 skipped, 0 failed\n",
        )
        self.assertEqual(len(output), 4)


class FormatNodeActionResultTest(TestCase):
    """
    Tests blockwart.cmdline.apply.format_node_action_result.
    """
    def test_values(self):
        result = MagicMock()
        result.actions_ok = 1
        result.actions_skipped = 2
        result.actions_failed = 3
        self.assertEqual(
            format_node_action_result(result),
            "1 ok, 2 skipped, 3 failed",
        )

    def test_zero(self):
        result = MagicMock()
        result.actions_ok = 0
        result.actions_skipped = 0
        result.actions_failed = 0
        self.assertEqual(
            format_node_action_result(result),
            "0 ok, 0 skipped, 0 failed",
        )


class FormatNodeItemResultTest(TestCase):
    """
    Tests blockwart.cmdline.apply.format_node_item_result.
    """
    def test_values(self):
        result = MagicMock()
        result.correct = 0
        result.fixed = 1
        result.skipped = 2
        result.unfixable = 3
        result.failed = 4
        self.assertEqual(
            format_node_item_result(result),
            "0 correct, 1 fixed, 2 skipped, 3 unfixable, 4 failed",
        )

    def test_zero(self):
        result = MagicMock()
        result.correct = 0
        result.fixed = 0
        result.skipped = 0
        result.unfixable = 0
        result.failed = 0
        self.assertEqual(
            format_node_item_result(result),
            "0 correct, 0 fixed, 0 skipped, 0 unfixable, 0 failed",
        )
