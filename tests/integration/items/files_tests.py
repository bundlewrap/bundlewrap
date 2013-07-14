from getpass import getuser
from platform import system
from tempfile import mkstemp
from unittest import TestCase

from mock import MagicMock

from blockwart.items import files
from blockwart.node import Node


class StatTest(TestCase):
    """
    Tests blockwart.items.files.stat.
    """
    def test_stat(self):
        if system() == "Darwin":
            return  # stat on Mac OS X is incompatible
        node = Node(MagicMock(), "localhost")
        f, filepath = mkstemp()
        stat_result = files.stat(node, filepath)
        self.assertEqual(stat_result['owner'], getuser())
        self.assertTrue(stat_result['mode'].isdigit())
