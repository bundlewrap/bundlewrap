from os.path import join
from shutil import rmtree
from tempfile import mkdtemp
from unittest import TestCase

from blockwart.utils import cached_property, import_module


class CachedPropertyTest(TestCase):
    """
    Tests blockwart.utils.cached_property.
    """
    def test_called_once(self):
        class ExampleClass(object):
            def __init__(self):
                self.counter = 0

            @cached_property
            def testprop(self):
                self.counter += 1
                return self.counter

        obj = ExampleClass()

        self.assertEqual(obj.testprop, 1)
        # a standard property would now return 2
        self.assertEqual(obj.testprop, 1)


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
