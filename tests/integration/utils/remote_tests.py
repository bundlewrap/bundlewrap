from getpass import getuser
from platform import system
from tempfile import mkstemp
from unittest import TestCase

from blockwart.node import Node
from blockwart.utils import remote


class StatTest(TestCase):
    """
    Tests blockwart.utils.remote.stat.
    """
    def test_stat(self):
        if system() == "Darwin":
            return  # stat on Mac OS X is incompatible
        node = Node("localhost")
        f, filepath = mkstemp()
        stat_result = remote.stat(node, filepath)
        self.assertEqual(stat_result['owner'], getuser())
        self.assertTrue(stat_result['mode'].isdigit())
