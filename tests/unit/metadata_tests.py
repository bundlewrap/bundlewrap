from unittest import TestCase

from bundlewrap import metadata
from bundlewrap.utils import _Atomic


class AtomicTest(TestCase):
    def test_invalid_atomic(self):
        with self.assertRaises(ValueError):
            metadata.atomic(1)
        with self.assertRaises(ValueError):
            metadata.atomic(None)
        with self.assertRaises(ValueError):
            metadata.atomic("str")

    def test_valid_atomic(self):
        self.assertTrue(isinstance(metadata.atomic([]), _Atomic))
        self.assertTrue(isinstance(metadata.atomic(tuple()), _Atomic))
        self.assertTrue(isinstance(metadata.atomic(set()), _Atomic))
        self.assertTrue(isinstance(metadata.atomic({}), _Atomic))
