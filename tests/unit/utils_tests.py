from os.path import join
from shutil import rmtree
from tempfile import mkdtemp
from unittest import TestCase

from blockwart.utils import cached_property, getattr_from_file


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


class GetAttrFromFileTest(TestCase):
    """
    Tests blockwart.utils.getattr_from_file.
    """
    def setUp(self):
        self.tmpdir = mkdtemp()
        self.fname = join(self.tmpdir, "test.py")

    def tearDown(self):
        rmtree(self.tmpdir)

    def test_default(self):
        with open(join(self.tmpdir, self.fname), 'w') as f:
            f.write("")
        with self.assertRaises(KeyError):
            getattr_from_file(self.fname, 'c')
        self.assertEqual(getattr_from_file(self.fname, 'c', None), None)
        self.assertEqual(getattr_from_file(self.fname, 'c', 49), 49)

    def test_import(self):
        with open(join(self.tmpdir, self.fname), 'w') as f:
            f.write("c = 47")
        self.assertEqual(getattr_from_file(self.fname, 'c'), 47)
        with open(join(self.tmpdir, self.fname), 'w') as f:
            f.write("c = 48")
        self.assertEqual(getattr_from_file(self.fname, 'c'), 48)
