from unittest import TestCase

from mock import MagicMock, patch

from blockwart.exceptions import RepositoryError
from blockwart.group import _build_error_chain, Group
from blockwart.node import Node
from blockwart.utils import names


class ErrorChainTest(TestCase):
    """
    Tests blockwart.group._build_error_chain.
    """
    def test_direct_loop(self):
        self.assertEqual(
            _build_error_chain(
                "group1",
                "group1",
                [],
            ),
            ["group1", "group1"],
        )

    def test_simple_indirect_loop(self):
        self.assertEqual(
            _build_error_chain(
                "group1",
                "group2",
                ["group1"],
            ),
            ["group1", "group2", "group1"],
        )

    def test_deep_indirect_loop(self):
        self.assertEqual(
            _build_error_chain(
                "group1",
                "group3",
                ["group1", "group2"],
            ),
            ["group1", "group2", "group3", "group1"],
        )

    def test_deep_indirect_inner_loop(self):
        self.assertEqual(
            _build_error_chain(
                "group2",
                "group3",
                ["group1", "group2"],
            ),
            ["group2", "group3", "group2"],
        )


class HierarchyTest(TestCase):
    """
    Tests subgroup functionality of blockwart.group.Group.
    """
    def test_no_subgroups(self):
        class FakeRepo(MagicMock):
            def get_group(self, name):
                return Group(self, name, {})

        repo = FakeRepo()
        group = repo.get_group("group1")
        self.assertEqual(list(names(group.subgroups)), [])

    def test_simple_subgroups(self):
        class FakeRepo(object):
            def get_group(self, name):
                subgroups = []
                if name == "group1":
                    subgroups = ["group2", "group3"]
                return Group(self, name, {'subgroups': subgroups})

        repo = FakeRepo()
        group = repo.get_group("group1")
        self.assertEqual(list(names(group.subgroups)), ["group2", "group3"])

    def test_nested_subgroups(self):
        class FakeRepo(object):
            def get_group(self, name):
                subgroups = []
                if name == "group1":
                    subgroups = ["group2"]
                elif name == "group2":
                    subgroups = ["group3"]
                return Group(self, name, {'subgroups': subgroups})

        repo = FakeRepo()
        group = repo.get_group("group1")
        self.assertEqual(
            set(names(group.subgroups)),
            set(["group2", "group3"]),
        )

    def test_simple_subgroup_loop(self):
        class FakeRepo(object):
            def get_group(self, name):
                return Group(self, name, {'subgroups': ["group1"]})

        repo = FakeRepo()
        group = repo.get_group("group1")
        with self.assertRaises(RepositoryError):
            list(group.subgroups)

    def test_nested_subgroup_loop(self):
        class FakeRepo(object):
            def get_group(self, name):
                subgroups = []
                if name == "group1":
                    subgroups = ["group2"]
                elif name == "group2":
                    subgroups = ["group1"]
                return Group(self, name, {'subgroups': subgroups})

        repo = FakeRepo()
        group = repo.get_group("group1")
        with self.assertRaises(RepositoryError):
            list(group.subgroups)

    def test_deeply_nested_subgroup_loop_top(self):
        class FakeRepo(object):
            def get_group(self, name):
                subgroups = []
                if name == "group1":
                    subgroups = ["group2"]
                elif name == "group2":
                    subgroups = ["group3"]
                elif name == "group3":
                    subgroups = ["group4"]
                elif name == "group4":
                    subgroups = ["group1"]
                return Group(self, name, {'subgroups': subgroups})

        repo = FakeRepo()
        group = repo.get_group("group1")
        with self.assertRaises(RepositoryError):
            list(group.subgroups)

    def test_deeply_nested_subgroup_loop(self):
        class FakeRepo(object):
            def get_group(self, name):
                subgroups = []
                if name == "group1":
                    subgroups = ["group2"]
                elif name == "group2":
                    subgroups = ["group3"]
                elif name == "group3":
                    subgroups = ["group4"]
                elif name == "group4":
                    subgroups = ["group2"]
                return Group(self, name, {'subgroups': subgroups})

        repo = FakeRepo()
        group = repo.get_group("group1")
        with self.assertRaises(RepositoryError):
            list(group.subgroups)


class InitTest(TestCase):
    """
    Tests initalization of blockwart.group.Group.
    """
    @patch('blockwart.group.validate_name', return_value=False)
    def test_bad_bundle_name(self, *args):
        with self.assertRaises(RepositoryError):
            Group(MagicMock(), "name", {})

    def test_bundles(self):
        bundles = ("bundle1", "bundle2")
        infodict = {
            'bundles': bundles,
        }
        g = Group(None, "group1", infodict)
        self.assertEqual(g.bundle_names, bundles)


class MemberTest(TestCase):
    """
    Tests node membership functionality of blockwart.group.Group.
    """
    def test_static_members(self):
        class FakeRepo(object):
            def get_node(self, name):
                return name

        repo = FakeRepo()
        group = Group(repo, "group1", {'nodes': ("node2", "node1")})
        self.assertEqual(
            set(group._nodes_from_static_members),
            set(("node1", "node2")),
        )

    @patch("blockwart.group.Group._nodes_from_patterns", return_value=())
    def test_static_subgroup_members(self, *args):
        class FakeRepo(object):
            def get_group(self, name):
                return Group(self, name, {'nodes': ("node3", "node4")})

            def get_node(self, name):
                return name

        repo = FakeRepo()
        group = Group(repo, "group1", {'subgroups': ("group2",)})
        self.assertEqual(
            set(group._nodes_from_subgroups),
            set(("node3", "node4")),
        )

    @patch("blockwart.group.getattr_from_file", return_value={
        r".*": "all",
        "2$": "group2",
    })
    def test_pattern_members(self, *args):
        repo = MagicMock()
        repo.nodes = (
            Node(repo, "node1", {}),
            Node(repo, "node2", {}),
        )
        group = Group(repo, "all", {})
        self.assertEqual(
            list(names(group.nodes)),
            ["node1", "node2"],
        )
        group = Group(repo, "group2", {})
        self.assertEqual(
            list(names(group.nodes)),
            ["node2"],
        )
