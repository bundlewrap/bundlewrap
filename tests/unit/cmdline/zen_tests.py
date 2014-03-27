from unittest import TestCase

from blockwart.cmdline import zen


class ZenTest(TestCase):
    """
    Tests blockwart.cmdline.zen.bw_zen.
    """
    def test_zen(self):
        list(zen.bw_zen(None, None))
