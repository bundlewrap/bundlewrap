from os import chdir, getcwd, mkdir
from os.path import join
from shutil import rmtree
from tempfile import mkdtemp
from unittest import TestCase

from mock import MagicMock

from bundlewrap.cmdline.metadata import bw_metadata
from bundlewrap.repo import Repository


class MetadataTest(TestCase):
    def setUp(self):
        self.cwd = getcwd()
        self.tmpdir = mkdtemp()
        mkdir(join(self.tmpdir, "bundles"))
        mkdir(join(self.tmpdir, "libs"))
        with open(join(self.tmpdir, "libs", "mp.py"), 'w') as f:
            f.write("""
def mp(node_name, groups, metadata):
    metadata['node'] += 1
    metadata['group'] += 1
    return metadata
""")
        with open(join(self.tmpdir, "nodes.py"), 'w') as f:
            f.write("""
nodes = {
    "node1": {
        "metadata": {
            "node": 47,
        },
    },
    "node2": {
        "metadata": {
            "node": 47,
        },
    },
}
""")
        with open(join(self.tmpdir, "groups.py"), 'w') as f:
            f.write("""
groups = {
    "group1": {
        "members": ["node1"],
        "metadata": {
            "group": 42,
        },
        "metadata_processors": ["mp.mp"],
    },
    "group2": {
        "members": ["node2"],
        "metadata": {
            "group": 42,
        },
    },
}
""")

    def tearDown(self):
        chdir(self.cwd)
        rmtree(self.tmpdir)

    def test_group_metadata(self):
        r = Repository(self.tmpdir)
        args = MagicMock()
        args.target = "group1"
        result = "\n".join(list(bw_metadata(r, args)))
        self.assertFalse('"node": 47' in result)
        self.assertTrue('"group": 42' in result)

    def test_metadata_processor(self):
        r = Repository(self.tmpdir)
        args = MagicMock()
        args.target = "node1"
        result = "\n".join(list(bw_metadata(r, args)))
        self.assertTrue('"node": 48' in result)
        self.assertTrue('"group": 43' in result)

    def test_no_metadata_processor(self):
        r = Repository(self.tmpdir)
        args = MagicMock()
        args.target = "node2"
        result = "\n".join(list(bw_metadata(r, args)))
        self.assertTrue('"node": 47' in result)
        self.assertTrue('"group": 42' in result)

    def test_unknown_target(self):
        r = Repository(self.tmpdir)
        args = MagicMock()
        args.target = "node5000"
        result = list(bw_metadata(r, args))
        self.assertEqual(result[-1], 1)
