from os import remove
from tempfile import mkstemp
from unittest import TestCase

from blockwart.items import files
from blockwart.node import Node


class GetRemoteFileContentsTest(TestCase):
    def test_get_content(self):
        handle, target_file = mkstemp()
        with open(target_file, 'w') as f:
            f.write("47")
        n = Node(None, 'localhost', {})
        try:
            self.assertEqual(
                files.get_remote_file_contents(n, target_file),
                "47",
            )
        finally:
            remove(target_file)
