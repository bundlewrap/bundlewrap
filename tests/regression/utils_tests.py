from cPickle import dumps
from unittest import TestCase

from mock import MagicMock

from blockwart import utils


class CachedPropExampleClass(object):
    method = MagicMock(return_value=47)

    @utils.cached_property
    def genfunc(self):
        for i in range(3):
            yield self.method()

    @utils.cached_property
    def tru(self):
        return True


class CachedPropertyTest(TestCase):
    """
    Tests blockwart.utils.utils.cached_property.
    """
    def test_generator(self):
        """
        Verifies that a generator returned from a cached property can be
        used multiple times.
        """
        obj = CachedPropExampleClass()
        self.assertEqual(obj.genfunc, (47, 47, 47))
        self.assertEqual(obj.method.call_count, 3)
        self.assertEqual(obj.genfunc, (47, 47, 47))
        self.assertEqual(obj.method.call_count, 3)

    def test_pickleable(self):
        obj = CachedPropExampleClass()
        obj.tru
        dumps(obj)
