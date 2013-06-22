from unittest import TestCase

from mock import MagicMock

from blockwart.cmdline import run


class RunTest(TestCase):
    """
    Tests blockwart.cmdline.run.bw_run.
    """
    def test_single_node(self):
        args = MagicMock()
        args.target = "node1"
        node = MagicMock()
        repo = MagicMock()
        repo.get_node = MagicMock(return_value=node)
        run.bw_run(repo, args)
        node.run.assert_called_once()
