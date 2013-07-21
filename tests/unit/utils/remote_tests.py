from os import remove
from tempfile import mkstemp
from unittest import TestCase

from mock import MagicMock

from blockwart.node import Node
from blockwart.utils import remote


class ExistsTest(TestCase):
    """
    Tests blockwart.utils.remote.exists.
    """
    def test_exists(self):
        _, filename = mkstemp()
        node = Node(MagicMock(), "localhost")
        self.assertTrue(remote.exists(node, filename))

    def test_doesnt_exist(self):
        _, filename = mkstemp()
        remove(filename)
        node = Node(MagicMock(), "localhost")
        self.assertFalse(remote.exists(node, filename))
