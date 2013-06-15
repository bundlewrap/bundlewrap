from unittest import TestCase

from blockwart.exceptions import RepositoryError
from blockwart.group import _build_error_chain, Group
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
        class FakeRepo(object):
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
