from unittest import TestCase

from mock import MagicMock

from blockwart.commands import run
from blockwart.node import RunResult


class RunTest(TestCase):
    """
    Tests blockwart.commands.run.
    """
    def test_run_single_node(self):
        node_name = "bananastand"
        command = "burn down"
        output = "money"
        run_res = RunResult()
        run_res.stdout = output

        repo = MagicMock()
        node = MagicMock()
        node.run = MagicMock(return_value=run_res)
        repo.get_node = MagicMock(return_value=node)

        result = run(repo, node_name, command)
        self.assertEqual(result, output)
        repo.get_node.assert_called_with(node_name)
        node.run.assert_called_with(command)
