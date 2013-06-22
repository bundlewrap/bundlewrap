from unittest import TestCase

from mock import MagicMock

from blockwart import utils


class CachedPropertyTest(TestCase):
    """
    Tests blockwart.utils.utils.cached_property.
    """
    def test_generator(self):
        """
        Verifies that a generator returned from a cached property can be
        used multiple times.
        """
        class ExampleClass(object):
            method = MagicMock(return_value=47)

            @utils.cached_property
            def testprop(self):
                for i in range(3):
                    yield self.method()

        obj = ExampleClass()
        self.assertEqual(obj.testprop, (47, 47, 47))
        self.assertEqual(obj.method.call_count, 3)
        self.assertEqual(obj.testprop, (47, 47, 47))
        self.assertEqual(obj.method.call_count, 3)
