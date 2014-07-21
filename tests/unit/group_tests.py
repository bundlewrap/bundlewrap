from unittest import TestCase

from mock import patch

from bundlewrap.exceptions import RepositoryError
from bundlewrap.group import _build_error_chain, Group
from bundlewrap.node import Node
from bundlewrap.repo import Repository
from bundlewrap.utils import names


class ErrorChainTest(TestCase):
    """
    Tests bundlewrap.group._build_error_chain.
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
    Tests subgroup functionality of bundlewrap.group.Group.
    """
    def test_no_subgroups(self):
        repo = Repository()
        repo.add_group(Group("group1", {'subgroups': []}))
        group = repo.get_group("group1")
        self.assertEqual(list(names(group.subgroups)), [])

    def test_simple_subgroups(self):
        repo = Repository()
        repo.add_group(Group("group1", {'subgroups': ["group2", "group3"]}))
        repo.add_group(Group("group2"))
        repo.add_group(Group("group3"))
        group = repo.get_group("group1")
        self.assertEqual(list(names(group.subgroups)), ["group2", "group3"])

    def test_nested_subgroups(self):
        repo = Repository()
        repo.add_group(Group("group1", {'subgroups': ["group2"]}))
        repo.add_group(Group("group2", {'subgroups': ["group3"]}))
        repo.add_group(Group("group3", {'subgroups': []}))
        group = repo.get_group("group1")
        self.assertEqual(
            set(names(group.subgroups)),
            set(["group2", "group3"]),
        )

    def test_simple_subgroup_loop(self):
        repo = Repository()
        repo.add_group(Group("group1", {'subgroups': ["group1"]}))
        group = repo.get_group("group1")
        with self.assertRaises(RepositoryError):
            list(group.subgroups)

    def test_nested_subgroup_loop(self):
        repo = Repository()
        repo.add_group(Group("group1", {'subgroups': ["group2"]}))
        repo.add_group(Group("group2", {'subgroups': ["group1"]}))
        group = repo.get_group("group1")
        with self.assertRaises(RepositoryError):
            list(group.subgroups)

    def test_deeply_nested_subgroup_loop_top(self):
        repo = Repository()
        repo.add_group(Group("group1", {'subgroups': ["group2"]}))
        repo.add_group(Group("group2", {'subgroups': ["group3"]}))
        repo.add_group(Group("group3", {'subgroups': ["group4"]}))
        repo.add_group(Group("group4", {'subgroups': ["group1"]}))
        group = repo.get_group("group1")
        with self.assertRaises(RepositoryError):
            list(group.subgroups)

    def test_deeply_nested_subgroup_loop(self):
        repo = Repository()
        repo.add_group(Group("group1", {'subgroups': ["group2"]}))
        repo.add_group(Group("group2", {'subgroups': ["group3"]}))
        repo.add_group(Group("group3", {'subgroups': ["group4"]}))
        repo.add_group(Group("group4", {'subgroups': ["group2"]}))
        group = repo.get_group("group1")
        with self.assertRaises(RepositoryError):
            list(group.subgroups)


class InitTest(TestCase):
    """
    Tests initalization of bundlewrap.group.Group.
    """
    @patch('bundlewrap.group.validate_name', return_value=False)
    def test_bad_bundle_name(self, *args):
        with self.assertRaises(RepositoryError):
            Group("name", {})

    def test_bundles(self):
        bundles = ("bundle1", "bundle2")
        infodict = {
            'bundles': bundles,
        }
        g = Group("group1", infodict)
        self.assertEqual(g.bundle_names, bundles)


class MemberTest(TestCase):
    """
    Tests node membership functionality of bundlewrap.group.Group.
    """
    def test_static_members(self):
        repo = Repository()
        node1 = Node("node1")
        node2 = Node("node2")
        repo.add_node(node1)
        repo.add_node(node2)
        group = Group("group1", {'members': ("node2", "node1")})
        repo.add_group(group)
        self.assertEqual(
            set(group._nodes_from_static_members),
            set((node1, node2)),
        )

    def test_static_subgroup_members(self, *args):
        repo = Repository()
        group1 = Group("group1", {'subgroups': ("group2",)})
        node3 = Node("node3")
        node4 = Node("node4")
        repo.add_group(group1)
        repo.add_group(Group("group2", {'members': ("node3", "node4")}))
        repo.add_node(node3)
        repo.add_node(node4)
        repo.add_node(Node("node5"))
        self.assertEqual(
            set(group1._nodes_from_subgroups),
            set((node3, node4)),
        )

    def test_pattern_members(self, *args):
        repo = Repository()
        repo.add_node(Node("node1"))
        repo.add_node(Node("node2"))
        group = Group("all", { 'member_patterns': (r".*",) })
        repo.add_group(group)
        self.assertEqual(
            list(names(group.nodes)),
            ["node1", "node2"],
        )
        group2 = Group("group2", { 'member_patterns': (r".*2",)} )
        repo.add_group(group2)
        self.assertEqual(
            list(names(group2.nodes)),
            ["node2"],
        )
