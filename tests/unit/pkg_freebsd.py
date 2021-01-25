from bundlewrap.items.pkg_freebsd import parse_pkg_name
from pytest import raises


def test_not_found():
    found, version = parse_pkg_name("tree", "zsh-5.8")
    assert found is False


def test_version():
    found, version = parse_pkg_name("tree", "tree-1.8.0")
    assert found is True
    assert version == "1.8.0"


def test_version_with_epoch():
    found, version = parse_pkg_name(
        "zsh-syntax-highlighting", "zsh-syntax-highlighting-0.7.1,1")
    assert found is True
    assert version == "0.7.1,1"


def test_illegal_no_version():
    with raises(AssertionError):
        parse_pkg_name("tree", "tree")
