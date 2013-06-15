from os.path import getsize, join
from shutil import rmtree
from tempfile import mkdtemp
from unittest import TestCase

from blockwart import repo
from blockwart.node import Node


class RepoTest(TestCase):
    def setUp(self):
        self.tmpdir = mkdtemp()

    def tearDown(self):
        rmtree(self.tmpdir)


class RepoCreateTest(RepoTest):
    def test_repo_create(self):
        r = repo.Repository(self.tmpdir)
        r.create()
        self.assertTrue(getsize(join(self.tmpdir, "nodes.py")) > 1)


class RepoDirTest(RepoTest):
    def test_repo_dir_check(self):
        with self.assertRaises(repo.RepositoryError):
            repo.Repository("/dev/null")
        repo.Repository(self.tmpdir)  # doesn't raise


class RepoNodesTest(RepoTest):
    def test_repo_get_node(self):
        r = repo.Repository(self.tmpdir)
        with open(join(r.path, repo.FILENAME_NODES), 'w') as f:
            f.write("nodes = {'node1': {}}")
        self.assertTrue(isinstance(r.get_node("node1"), Node))
        with self.assertRaises(repo.NoSuchNode):
            r.get_node("nosuchnode")

    def test_repo_load_nodes(self):
        r = repo.Repository(self.tmpdir)
        with open(join(r.path, repo.FILENAME_NODES), 'w') as f:
            f.write("nodes = {'node1': {}, 'node2': {}}")
        self.assertEqual(r.node_dict['node1'].name, 'node1')

    def test_repo_missing_nodes(self):
        r = repo.Repository(self.tmpdir)
        with open(join(r.path, repo.FILENAME_NODES), 'w') as f:
            f.write("")
        with self.assertRaises(repo.RepositoryError):
            r.node_dict
