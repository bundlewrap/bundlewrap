from os import remove, symlink
from platform import system
from tempfile import mkstemp
from unittest import TestCase

from mock import MagicMock, patch

from blockwart.node import Node
from blockwart.operations import RunResult
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


class PathInfoTest(TestCase):
    """
    Tests blockwart.utils.remote.PathInfo.
    """
    @patch('blockwart.utils.remote.stat')
    @patch('blockwart.utils.remote.get_path_type', return_value=(
        'nonexistent', ""))
    def test_nonexistent(self, stat, get_path_type):
        p = remote.PathInfo(MagicMock(), "/")
        self.assertFalse(p.exists)
        self.assertFalse(p.is_binary_file)
        self.assertFalse(p.is_directory)
        self.assertFalse(p.is_file)
        self.assertFalse(p.is_symlink)
        self.assertFalse(p.is_text_file)
        with self.assertRaises(ValueError):
            p.symlink_target

    @patch('blockwart.utils.remote.stat')
    @patch('blockwart.utils.remote.get_path_type', return_value=(
        'file', "data"))
    def test_binary(self, stat, get_path_type):
        p = remote.PathInfo(MagicMock(), "/")
        self.assertTrue(p.exists)
        self.assertTrue(p.is_binary_file)
        self.assertFalse(p.is_directory)
        self.assertTrue(p.is_file)
        self.assertFalse(p.is_symlink)
        self.assertFalse(p.is_text_file)
        with self.assertRaises(ValueError):
            p.symlink_target

    @patch('blockwart.utils.remote.stat')
    @patch('blockwart.utils.remote.get_path_type', return_value=(
        'directory', "directory"))
    def test_directory(self, stat, get_path_type):
        p = remote.PathInfo(MagicMock(), "/")
        self.assertTrue(p.exists)
        self.assertFalse(p.is_binary_file)
        self.assertTrue(p.is_directory)
        self.assertFalse(p.is_file)
        self.assertFalse(p.is_symlink)
        self.assertFalse(p.is_text_file)
        with self.assertRaises(ValueError):
            p.symlink_target

    @patch('blockwart.utils.remote.stat')
    @patch('blockwart.utils.remote.get_path_type', return_value=(
        'file', "ASCII English text"))
    def test_text(self, stat, get_path_type):
        p = remote.PathInfo(MagicMock(), "/")
        self.assertTrue(p.exists)
        self.assertFalse(p.is_binary_file)
        self.assertFalse(p.is_directory)
        self.assertTrue(p.is_file)
        self.assertFalse(p.is_symlink)
        self.assertTrue(p.is_text_file)
        with self.assertRaises(ValueError):
            p.symlink_target

    @patch('blockwart.utils.remote.stat')
    @patch('blockwart.utils.remote.get_path_type', return_value=(
        'symlink', "symbolic link to `/47'"))
    def test_symlink_normal(self, stat, get_path_type):
        p = remote.PathInfo(MagicMock(), "/")
        self.assertTrue(p.exists)
        self.assertFalse(p.is_binary_file)
        self.assertFalse(p.is_directory)
        self.assertFalse(p.is_file)
        self.assertTrue(p.is_symlink)
        self.assertFalse(p.is_text_file)
        self.assertEqual(p.symlink_target, "/47")

    @patch('blockwart.utils.remote.stat')
    @patch('blockwart.utils.remote.get_path_type', return_value=(
        'symlink', "broken symbolic link to `/47'"))
    def test_symlink_broken(self, stat, get_path_type):
        p = remote.PathInfo(MagicMock(), "/")
        self.assertTrue(p.exists)
        self.assertFalse(p.is_binary_file)
        self.assertFalse(p.is_directory)
        self.assertFalse(p.is_file)
        self.assertTrue(p.is_symlink)
        self.assertFalse(p.is_text_file)
        self.assertEqual(p.symlink_target, "/47")

    @patch('blockwart.utils.remote.stat')
    @patch('blockwart.utils.remote.get_path_type', return_value=(
        'symlink', "symbolic link to /47"))
    def test_symlink_noquotes(self, stat, get_path_type):
        p = remote.PathInfo(MagicMock(), "/")
        self.assertTrue(p.exists)
        self.assertFalse(p.is_binary_file)
        self.assertFalse(p.is_directory)
        self.assertFalse(p.is_file)
        self.assertTrue(p.is_symlink)
        self.assertFalse(p.is_text_file)
        self.assertEqual(p.symlink_target, "/47")

    @patch('blockwart.utils.remote.stat')
    @patch('blockwart.utils.remote.get_path_type', return_value=(
        'symlink', "broken symbolic link to /47"))
    def test_symlink_noquotes_broken(self, stat, get_path_type):
        p = remote.PathInfo(MagicMock(), "/")
        self.assertTrue(p.exists)
        self.assertFalse(p.is_binary_file)
        self.assertFalse(p.is_directory)
        self.assertFalse(p.is_file)
        self.assertTrue(p.is_symlink)
        self.assertFalse(p.is_text_file)
        self.assertEqual(p.symlink_target, "/47")

    def test_sha1(self):
        if system() == "Darwin":
            # no 'sha1sum' on Mac OS
            return
        _, filename = mkstemp()
        with open(filename, 'w') as f:
            f.write("47")
        node = Node(MagicMock(), "localhost")
        p = remote.PathInfo(node, filename)
        self.assertEqual(
            p.sha1,
            "827bfc458708f0b442009c9c9836f7e4b65557fb",
        )

    @patch('blockwart.utils.remote.stat', return_value={
        'owner': "foo",
        'group': "bar",
        'mode': "4747",
        'size': 4848,
    })
    @patch('blockwart.utils.remote.get_path_type', return_value=(
        'file', "data"))
    def test_stat(self, stat, get_path_type):
        p = remote.PathInfo(MagicMock(), "/")
        self.assertEqual(p.owner, "foo")
        self.assertEqual(p.group, "bar")
        self.assertEqual(p.mode, "4747")
        self.assertEqual(p.size, 4848)


class StatTest(TestCase):
    """
    Tests blockwart.utils.remote.stat.
    """
    def test_long_mode(self):
        node = MagicMock()
        run_result = RunResult()
        run_result.stdout = "user:group:7777:1234"
        node.run.return_value = run_result
        stat_result = remote.stat(node, "/dev/null")
        self.assertEqual(stat_result, {
            'owner': "user",
            'group': "group",
            'mode': "7777",
            'size': 1234,
        })

    def test_short_mode(self):
        node = MagicMock()
        run_result = RunResult()
        run_result.stdout = "user:group:666:4321"
        node.run.return_value = run_result
        stat_result = remote.stat(node, "/dev/null")
        self.assertEqual(stat_result, {
            'owner': "user",
            'group': "group",
            'mode': "0666",
            'size': 4321,
        })
