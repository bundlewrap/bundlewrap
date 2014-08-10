from getpass import getuser
from os import mkdir, remove
from os.path import join
from platform import system
from tempfile import mkdtemp, mkstemp
from unittest import TestCase

from mock import MagicMock

from bundlewrap.items import files
from bundlewrap.node import Node
from bundlewrap.repo import Repository


class GetRemoteFileContentsTest(TestCase):
    def test_get_content(self):
        handle, target_file = mkstemp()
        with open(target_file, 'w') as f:
            f.write("47")
        n = Node('localhost', {})
        try:
            self.assertEqual(
                files.get_remote_file_contents(n, target_file),
                "47",
            )
        finally:
            remove(target_file)


class FileCreateTest(TestCase):
    def test_create(self):
        if system() == "Darwin":
            return
        handle, target_file = mkstemp()
        remove(target_file)
        bundle = MagicMock()
        bundle.bundle_dir = mkdtemp()
        bundle.bundle_data_dir = mkdtemp()
        bundle.node = Node('localhost')
        Repository().add_node(bundle.node)
        item = files.File(
            bundle,
            target_file,
            {
                'content_type': 'mako',
                'owner': getuser(),
                'source': 'my_template',
            },
        )
        mkdir(item.item_dir)
        with open(join(item.item_dir, "my_template"), 'w') as f:
            f.write("Hi from ${node.name}!")
        item.apply(interactive=False)
        with open(target_file) as f:
            content = f.read()
        try:
            self.assertEqual(content, "Hi from localhost!")
        finally:
            remove(target_file)
