from pytest import raises

from bundlewrap.exceptions import RepositoryError
from bundlewrap.group import Group
from bundlewrap.node import Node
from bundlewrap.repo import Repository


def _repo_with(groups=None, nodes=None):
    repo = Repository()
    for name, attrs in (groups or {}).items():
        repo.add_group(Group(name, attrs, repo=repo))
    for name, attrs in (nodes or {}).items():
        repo.add_node(Node(name, attrs, repo=repo))
    return repo


def test_key_attrs_default_to_none():
    node = _repo_with(nodes={"node1": {}}).get_node("node1")
    assert node.generate_key is None
    assert node.encrypt_key is None


def test_key_attrs_from_node():
    node = _repo_with(nodes={
        "node1": {"generate_key": "gen1", "encrypt_key": "enc1"},
    }).get_node("node1")
    assert node.generate_key == "gen1"
    assert node.encrypt_key == "enc1"


def test_key_attrs_inherited_from_group():
    node = _repo_with(
        groups={"group1": {"generate_key": "gen1", "encrypt_key": "enc1"}},
        nodes={"node1": {"groups": ["group1"]}},
    ).get_node("node1")
    assert node.generate_key == "gen1"
    assert node.encrypt_key == "enc1"


def test_key_attrs_node_overrides_group():
    node = _repo_with(
        groups={"group1": {"generate_key": "gen1", "encrypt_key": "enc1"}},
        nodes={"node1": {"groups": ["group1"], "generate_key": "gen2"}},
    ).get_node("node1")
    assert node.generate_key == "gen2"
    assert node.encrypt_key == "enc1"


def test_key_attrs_subgroup_overrides_supergroup():
    node = _repo_with(
        groups={
            "parent": {"generate_key": "gen-parent", "subgroups": ["child"]},
            "child": {"generate_key": "gen-child"},
        },
        nodes={"node1": {"groups": ["child"]}},
    ).get_node("node1")
    assert node.generate_key == "gen-child"


def test_key_attrs_must_be_strings():
    with raises(ValueError):
        Node("node1", {"generate_key": 42}, repo=Repository())
    with raises(ValueError):
        Group("group1", {"encrypt_key": ["a", "b"]}, repo=Repository())


def test_key_attrs_must_not_be_empty():
    with raises(RepositoryError):
        Node("node1", {"generate_key": ""}, repo=Repository())
    with raises(RepositoryError):
        Group("group1", {"encrypt_key": ""}, repo=Repository())
