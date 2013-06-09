from os.path import join
from shutil import rmtree
from tempfile import mkdtemp
from unittest import TestCase

from blockwart.utils import import_module


class ImportTest(TestCase):
    def setUp(self):
        self.tmpdir = mkdtemp()
        with open(join(self.tmpdir, "test.py"), 'w') as f:
            f.write("c = 47")

    def tearDown(self):
        rmtree(self.tmpdir)

    def test_import(self):
        m = import_module(join(self.tmpdir, "test.py"))
        self.assertEqual(m.c, 47)
