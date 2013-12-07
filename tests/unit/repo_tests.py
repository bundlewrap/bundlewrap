from os import mkdir
from os.path import getsize, join
from shutil import rmtree
from tempfile import mkdtemp
from unittest import TestCase

from mock import patch

from blockwart import repo
from blockwart.items import Item
from blockwart.exceptions import RepositoryError
from blockwart.node import Node


class RepoTest(TestCase):
    def setUp(self):
        self.tmpdir = mkdtemp()

    def tearDown(self):
        rmtree(self.tmpdir)


class LibsProxyTest(RepoTest):
    """
    Tests blockwart.repo.LibsProxy.
    """
    def test_module(self):
        with open(join(self.tmpdir, "proxytest.py"), 'w') as f:
            f.write("answer = 42")
        p = repo.LibsProxy(self.tmpdir)
        self.assertEqual(p.proxytest.answer, 42)


class RepoBundlesTest(RepoTest):
    """
    Tests blockwart.repo.Repository.bundle_names.
    """
    def test_repo_create(self, *args):
        bundles = ("bundle1", "bundle2")
        r = repo.Repository(self.tmpdir, skip_validation=True)
        mkdir(r.bundles_dir)
        for bundle in bundles:
            mkdir(join(r.bundles_dir, bundle))
        self.assertEqual(
            set(r.bundle_names),
            set(bundles),
        )


class RepoItemClasses1Test(RepoTest):
    """
    Tests blockwart.repo.Repository.item_classes.
    """
    def test_no_custom(self):
        r = repo.Repository(self.tmpdir, skip_validation=True)
        self.assertGreater(len(r.item_classes), 0)
        for cls in r.item_classes:
            self.assertNotEqual(cls, Item)


class RepoItemClasses2Test(RepoTest):
    """
    Tests blockwart.repo.Repository.item_classes.
    """
    def test_with_custom(self):
        r = repo.Repository(self.tmpdir, skip_validation=True)
        ci_dir = join(self.tmpdir, "items")
        mkdir(ci_dir)
        with open(join(ci_dir, "good1.py"), 'w') as f:
            f.write("from blockwart.items import Item\n"
                    "class GoodTestItem(Item): bad = False\n")
        with open(join(ci_dir, "_bad1.py"), 'w') as f:
            f.write("from blockwart.items import Item\n"
                    "class BadTestItem(Item): bad = True\n")
        with open(join(ci_dir, "bad2.py"), 'w') as f:
            f.write("from blockwart.items import Item\n"
                    "class _BadTestItem(Item): bad = True\n")
        self.assertGreater(len(r.item_classes), 0)
        for cls in r.item_classes:
            if hasattr(cls, 'bad'):
                self.assertFalse(cls.bad)
            self.assertTrue(issubclass(cls, Item))


class RepoCreateTest(RepoTest):
    """
    Tests blockwart.repo.Repository.create().
    """
    def test_repo_create(self):
        r = repo.Repository(self.tmpdir, skip_validation=True)
        r.create()
        self.assertTrue(getsize(join(self.tmpdir, "nodes.py")) > 1)


class RepoGroupsTest(RepoTest):
    def test_node_group_name_clash(self):
        r = repo.Repository(self.tmpdir, skip_validation=True)
        with open(r.groups_file, 'w') as f:
            f.write("groups = {'highlander': {}}")
        with open(r.nodes_file, 'w') as f:
            f.write("nodes = {'highlander': {}}")
        with self.assertRaises(RepositoryError):
            r.groups


class RepoNodesTest(RepoTest):
    def test_repo_get_node(self):
        """
        Tests blockwart.repo.Repository.get_node.
        """
        r = repo.Repository(self.tmpdir, skip_validation=True)
        with open(join(r.path, repo.FILENAME_NODES), 'w') as f:
            f.write("nodes = {'node1': {}}")
        self.assertTrue(isinstance(r.get_node("node1"), Node))
        with self.assertRaises(repo.NoSuchNode):
            r.get_node("nosuchnode")

    def test_repo_load_nodes(self):
        """
        Tests blockwart.repo.Repository.node_dict.
        """
        r = repo.Repository(self.tmpdir, skip_validation=True)
        with open(join(r.path, repo.FILENAME_NODES), 'w') as f:
            f.write("nodes = {'node1': {}, 'node2': {}}")
        self.assertEqual(r.node_dict['node1'].name, 'node1')

    def test_repo_missing_nodes(self):
        """
        Tests blockwart.repo.Repository.node_dict.
        """
        r = repo.Repository(self.tmpdir, skip_validation=True)
        with open(join(r.path, repo.FILENAME_NODES), 'w') as f:
            f.write("")
        with self.assertRaises(repo.RepositoryError):
            r.node_dict


class RepoValidationTest(RepoTest):
    """
    Tests the initialization mechanism of blockwart.repo.Repository.
    """
    @patch('tests.unit.repo_tests.repo.Repository.is_repo', return_value=True)
    def test_repo_init(self, *args):
        repo.Repository("/dev/null")

    @patch('tests.unit.repo_tests.repo.Repository.is_repo', return_value=False)
    def test_repo_init_skip_validation(self, *args):
        repo.Repository("/dev/null", skip_validation=True)

    def test_repo_nodir(self):
        self.assertFalse(repo.Repository.is_repo("/dev/null"))

    def test_repo(self):
        self.assertFalse(repo.Repository.is_repo(self.tmpdir))

        r = repo.Repository(self.tmpdir, skip_validation=True)

        with open(join(r.path, repo.FILENAME_NODES), 'w') as f:
            f.write("")
        self.assertFalse(repo.Repository.is_repo(self.tmpdir))

        with open(join(r.path, repo.FILENAME_GROUPS), 'w') as f:
            f.write("")
        self.assertTrue(repo.Repository.is_repo(self.tmpdir))
