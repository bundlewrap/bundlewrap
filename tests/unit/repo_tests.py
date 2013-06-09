from os.path import getsize, join
from shutil import rmtree
from tempfile import mkdtemp
from unittest import TestCase

from blockwart.repo import Repository, RepositoryError


class RepoTest(TestCase):
    def setUp(self):
        self.tmpdir = mkdtemp()

    def tearDown(self):
        rmtree(self.tmpdir)

    def test_repo_dir_check(self):
        with self.assertRaises(RepositoryError):
            Repository("/dev/null")
        Repository(self.tmpdir)  # doesn't raise

    def test_repo_create(self):
        repo = Repository(self.tmpdir)
        repo.create()
        self.assertTrue(getsize(join(self.tmpdir, "nodes.py")) > 1)
