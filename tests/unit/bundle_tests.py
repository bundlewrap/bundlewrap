from unittest import TestCase

from mock import MagicMock, patch

from blockwart.bundle import Bundle
from blockwart.exceptions import RepositoryError


class InitTest(TestCase):
    """
    Tests initialization of blockwart.bundle.Bundle.
    """
    @patch('blockwart.bundle.validate_name', return_value=False)
    def test_bad_bundle_name(self, *args):
        with self.assertRaises(RepositoryError):
            Bundle(MagicMock(), "name")
