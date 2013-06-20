from os import chdir
from os.path import getsize, join
from shutil import rmtree
from tempfile import mkdtemp
from unittest import TestCase

from blockwart.cmdline import main


class RepoCreateTest(TestCase):
    def setUp(self):
        self.tmpdir = mkdtemp()

    def tearDown(self):
        rmtree(self.tmpdir)

    def test_simple_create(self):
        chdir(self.tmpdir)
        main("repo", "create")
        self.assertTrue(getsize(join(self.tmpdir, "nodes.py")) > 1)
