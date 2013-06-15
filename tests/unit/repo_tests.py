from os.path import getsize, join
from shutil import rmtree
from tempfile import mkdtemp
from unittest import TestCase

from blockwart.node import Node
from blockwart.repo import NoSuchNode, Repository, RepositoryError


class RepoTest(TestCase):
    def setUp(self):
        self.tmpdir = mkdtemp()

    def tearDown(self):
        rmtree(self.tmpdir)


class RepoCreateTest(RepoTest):
    def test_repo_create(self):
        repo = Repository(self.tmpdir)
        repo.create()
        self.assertTrue(getsize(join(self.tmpdir, "nodes.py")) > 1)


class RepoDirTest(RepoTest):
    def test_repo_dir_check(self):
        with self.assertRaises(RepositoryError):
            Repository("/dev/null")
        Repository(self.tmpdir)  # doesn't raise


class RepoNodesTest(RepoTest):
    def test_repo_get_node(self):
        repo = Repository(self.tmpdir)
        with open(join(repo.path, "nodes.py"), 'w') as f:
            f.write("nodes = {'node1': {}}")
        self.assertTrue(isinstance(repo.get_node("node1"), Node))
        with self.assertRaises(NoSuchNode):
            repo.get_node("nosuchnode")

    def test_repo_load_nodes(self):
        repo = Repository(self.tmpdir)
        with open(join(repo.path, "nodes.py"), 'w') as f:
            f.write("nodes = {'node1': {}, 'node2': {}}")
        self.assertEqual(repo.node_dict['node1'].name, 'node1')

    def test_repo_missing_nodes(self):
        repo = Repository(self.tmpdir)
        with open(join(repo.path, "nodes.py"), 'w') as f:
            f.write("")
        with self.assertRaises(RepositoryError):
            repo.node_dict
