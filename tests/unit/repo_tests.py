from os.path import getsize, join
from shutil import rmtree
from tempfile import mkdtemp
from unittest import TestCase

from mock import patch

from blockwart import repo
from blockwart.node import Node


class RepoTest(TestCase):
    def setUp(self):
        self.tmpdir = mkdtemp()

    def tearDown(self):
        rmtree(self.tmpdir)


class RepoCreateTest(RepoTest):
    """
    Tests blockwart.repo.Repository.create().
    """
    def test_repo_create(self):
        r = repo.Repository(self.tmpdir, skip_validation=True)
        r.create()
        self.assertTrue(getsize(join(self.tmpdir, "nodes.py")) > 1)


class RepoNodesTest(RepoTest):
    def test_repo_get_node(self):
        """
        Tests blockwart.repo.Repository.get_node.
        """
        r = repo.Repository(self.tmpdir, skip_validation=True)
        with open(join(r.path, repo.FILENAME_NODES), 'w') as f:
            f.write("nodes = {'node1': {}}")
        self.assertTrue(isinstance(r.get_node("node1"), Node))
        with self.assertRaises(repo.NoSuchNode):
            r.get_node("nosuchnode")

    def test_repo_load_nodes(self):
        """
        Tests blockwart.repo.Repository.node_dict.
        """
        r = repo.Repository(self.tmpdir, skip_validation=True)
        with open(join(r.path, repo.FILENAME_NODES), 'w') as f:
            f.write("nodes = {'node1': {}, 'node2': {}}")
        self.assertEqual(r.node_dict['node1'].name, 'node1')

    def test_repo_missing_nodes(self):
        """
        Tests blockwart.repo.Repository.node_dict.
        """
        r = repo.Repository(self.tmpdir, skip_validation=True)
        with open(join(r.path, repo.FILENAME_NODES), 'w') as f:
            f.write("")
        with self.assertRaises(repo.RepositoryError):
            r.node_dict


class RepoValidationTest(RepoTest):
    """
    Tests the initialization mechanism of blockwart.repo.Repository.
    """
    @patch('tests.unit.repo_tests.repo.Repository.is_repo', return_value=True)
    def test_repo_init(self, *args):
        repo.Repository("/dev/null")

    @patch('tests.unit.repo_tests.repo.Repository.is_repo', return_value=False)
    def test_repo_init_skip_validation(self, *args):
        repo.Repository("/dev/null", skip_validation=True)

    def test_repo_nodir(self):
        self.assertFalse(repo.Repository.is_repo("/dev/null"))

    def test_repo(self):
        self.assertFalse(repo.Repository.is_repo(self.tmpdir))

        r = repo.Repository(self.tmpdir, skip_validation=True)

        with open(join(r.path, repo.FILENAME_NODES), 'w') as f:
            f.write("")
        self.assertFalse(repo.Repository.is_repo(self.tmpdir))

        with open(join(r.path, repo.FILENAME_GROUPS), 'w') as f:
            f.write("")
        self.assertTrue(repo.Repository.is_repo(self.tmpdir))
