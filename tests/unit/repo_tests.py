from os import mkdir
from os.path import join
from pickle import dumps, loads
from shutil import rmtree
from tempfile import mkdtemp
from unittest import TestCase

try:
    from unittest.mock import MagicMock
except ImportError:
    from mock import MagicMock

from bundlewrap import repo
from bundlewrap.items import Item
from bundlewrap.repo import Repository


class RepoTest(TestCase):
    def setUp(self):
        self.tmpdir = mkdtemp()

    def tearDown(self):
        rmtree(self.tmpdir)


class HooksProxyTest(RepoTest):
    """
    Tests bundlewrap.repo.HooksProxy.
    """
    def test_hook(self):
        with open(join(self.tmpdir, "hook1.py"), 'w') as f:
            f.write(
"""
def apply_start(arg, kwarg=0):
    with open("{}", 'w') as f:
        f.write(arg + kwarg)
""".format(join(self.tmpdir, "test.log"))
            )
        p = repo.HooksProxy(self.tmpdir)
        p.apply_start("foo", kwarg="bar")
        with open(join(self.tmpdir, "test.log")) as f:
            content = f.read()
        self.assertEqual(content, "foobar")

    def test_unpickle(self):
        with open(join(self.tmpdir, "hook2.py"), 'w') as f:
            f.write(
"""
def apply_start(arg, kwarg=0):
    with open("{}", 'w') as f:
        f.write(arg + kwarg)
""".format(join(self.tmpdir, "test2.log"))
            )
        p = repo.HooksProxy(self.tmpdir)
        p.apply_start("foo", kwarg="bar")

        pstr = dumps(p)
        p = loads(pstr)

        p.apply_start("bar", kwarg="foo")
        with open(join(self.tmpdir, "test2.log")) as f:
            content = f.read()
        self.assertEqual(content, "barfoo")

    def test_unknown(self):
        p = repo.HooksProxy(self.tmpdir)
        with self.assertRaises(AttributeError):
            p.foo()

    def test_not_existing(self):
        p = repo.HooksProxy(join(self.tmpdir, "404"))
        p.apply_start()


class LibsProxyTest(RepoTest):
    """
    Tests bundlewrap.repo.LibsProxy.
    """
    def test_module(self):
        with open(join(self.tmpdir, "proxytest.py"), 'w') as f:
            f.write("answer = 42")
        p = repo.LibsProxy(self.tmpdir)
        self.assertEqual(p.proxytest.answer, 42)


class RepoBundlesTest(RepoTest):
    """
    Tests bundlewrap.repo.Repository.bundle_names.
    """
    def test_repo_create(self, *args):
        bundles = ("bundle1", "bundle2")
        r = Repository.create(self.tmpdir)
        for bundle in bundles:
            mkdir(join(r.bundles_dir, bundle))
        r.populate_from_path(self.tmpdir)
        self.assertEqual(
            set(r.bundle_names),
            set(bundles),
        )


class RepoItemClasses2Test(RepoTest):
    """
    Tests bundlewrap.repo.Repository.item_classes.
    """
    def test_with_custom(self):
        r = Repository.create(self.tmpdir)
        with open(join(r.items_dir, "good1.py"), 'w') as f:
            f.write("from bundlewrap.items import Item\n"
                    "class GoodTestItem(Item): bad = False\n")
        with open(join(r.items_dir, "_bad1.py"), 'w') as f:
            f.write("from bundlewrap.items import Item\n"
                    "class BadTestItem(Item): bad = True\n")
        with open(join(r.items_dir, "bad2.py"), 'w') as f:
            f.write("from bundlewrap.items import Item\n"
                    "class _BadTestItem(Item): bad = True\n")
        r.populate_from_path(self.tmpdir)
        self.assertGreater(len(r.item_classes), 0)
        for cls in r.item_classes:
            if hasattr(cls, 'bad'):
                self.assertFalse(cls.bad)
            self.assertTrue(issubclass(cls, Item))


class RepoNodesWithAllGroupsTest(TestCase):
    def test_some_members(self):
        def _get_group(group_name):
            group = MagicMock()
            if group_name == "group1":
                group.nodes = ["node1", "node2", "node3"]
            if group_name == "group2":
                group.nodes = ["node2", "node3"]
            if group_name == "group3":
                group.nodes = ["node2", "node3", "node4"]
            return group
        r = Repository()
        r.get_group = _get_group

        self.assertEqual(
            r.nodes_in_all_groups(["group1", "group2", "group3"]),
            ["node2", "node3"],
        )

    def test_no_members(self):
        def _get_group(group_name):
            group = MagicMock()
            if group_name == "group1":
                group.nodes = ["node1", "node2", "node3"]
            if group_name == "group2":
                group.nodes = ["node4"]
            if group_name == "group3":
                group.nodes = ["node2", "node3"]
            return group
        r = Repository()
        r.get_group = _get_group

        self.assertEqual(
            r.nodes_in_all_groups(["group1", "group2", "group3"]),
            [],
        )
