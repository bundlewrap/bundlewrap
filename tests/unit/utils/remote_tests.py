from os import remove, symlink
from tempfile import mkstemp
from unittest import TestCase

from mock import MagicMock

from blockwart.node import Node
from blockwart.utils import remote


class GetPathTypeTest(TestCase):
    """
    Tests blockwart.utils.remote.get_path_type.
    """
    def test_directory(self):
        node = Node(MagicMock(), "localhost")
        self.assertEqual(
            remote.get_path_type(node, "/")[0],
            'directory',
        )

    def test_doesnt_exist(self):
        _, filename = mkstemp()
        remove(filename)
        node = Node(MagicMock(), "localhost")
        self.assertEqual(
            remote.get_path_type(node, filename)[0],
            'nonexistent',
        )

    def test_file(self):
        _, filename = mkstemp()
        node = Node(MagicMock(), "localhost")
        self.assertEqual(
            remote.get_path_type(node, filename)[0],
            'file',
        )

    def test_special(self):
        node = Node(MagicMock(), "localhost")
        self.assertEqual(
            remote.get_path_type(node, "/dev/null")[0],
            'other',
        )

    def test_symlink(self):
        _, filename1 = mkstemp()
        _, filename2 = mkstemp()
        remove(filename2)
        symlink(filename1, filename2)
        node = Node(MagicMock(), "localhost")
        self.assertEqual(
            remote.get_path_type(node, filename2)[0],
            'symlink',
        )
