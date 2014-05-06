from os import chdir, getcwd
from os.path import getsize, isfile, isdir, join
from shutil import rmtree
from tempfile import mkdtemp
from unittest import TestCase

from mock import patch

from blockwart.cmdline import main


class RepoCreateTest(TestCase):
    def setUp(self):
        self.cwd = getcwd()
        self.tmpdir = mkdtemp()

    def tearDown(self):
        chdir(self.cwd)
        rmtree(self.tmpdir)

    @patch('blockwart.cmdline.exit')
    def test_simple_create(self, exit):
        chdir(self.tmpdir)
        main("repo", "create")
        self.assertTrue(getsize(join(self.tmpdir, "nodes.py")) > 1)


class RepoBundleCreateTest(TestCase):
    def setUp(self):
        self.cwd = getcwd()
        self.tmpdir = mkdtemp()

    def tearDown(self):
        chdir(self.cwd)
        rmtree(self.tmpdir)

    @patch('blockwart.cmdline.exit')
    def test_simple_create(self, exit):
        chdir(self.tmpdir)
        main("repo", "create")
        self.assertFalse(isfile(join(self.tmpdir, "bundles", "test", "bundle.py")))
        self.assertFalse(isdir(join(self.tmpdir, "bundles", "test", "files")))
        main("repo", "bundle", "create", "test")
        self.assertTrue(isfile(join(self.tmpdir, "bundles", "test", "bundle.py")))
        self.assertTrue(isdir(join(self.tmpdir, "bundles", "test", "files")))


class RepoNotFoundTest(TestCase):
    def setUp(self):
        self.cwd = getcwd()
        self.tmpdir = mkdtemp()

    def tearDown(self):
        chdir(self.cwd)
        rmtree(self.tmpdir)

    def test_exit(self):
        chdir(self.tmpdir)
        with self.assertRaises(SystemExit):
            main("repo", "debug")
