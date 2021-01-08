from bundlewrap.metadata import path_to_tuple
from bundlewrap.metagen import reactors_for_path
from bundlewrap.utils.text import randstr


class MockReactor:
    def __init__(self, provides):
        self._provides = {path_to_tuple(path) for path in provides}


def _make_reactor(*provides):
    return (randstr(length=6), MockReactor(provides))


def test_reactors_for_path_simple():
    reactor_a = _make_reactor("a")
    reactor_b = _make_reactor("b")
    assert list(reactors_for_path([reactor_a, reactor_b], path_to_tuple("a"))) == [reactor_a]
    assert list(reactors_for_path([reactor_a, reactor_b], path_to_tuple("b"))) == [reactor_b]
    assert list(reactors_for_path([reactor_a, reactor_b], path_to_tuple("c"))) == []


def test_reactors_for_path_narrow():
    reactor_a = _make_reactor("a")
    assert list(reactors_for_path([reactor_a], path_to_tuple("a/b"))) == [reactor_a]


def test_reactors_for_path_wide():
    reactor_a = _make_reactor("a/b")
    assert list(reactors_for_path([reactor_a], path_to_tuple("a"))) == [reactor_a]
    assert list(reactors_for_path([reactor_a], path_to_tuple("b"))) == []
    assert list(reactors_for_path([reactor_a], path_to_tuple("a/b"))) == [reactor_a]
    assert list(reactors_for_path([reactor_a], path_to_tuple("a/b/c"))) == [reactor_a]


def test_reactors_wildcard():
    reactor_a = _make_reactor("a/*/c")
    reactor_b = _make_reactor("*/b")
    reactor_c = _make_reactor("*/*/c")

    assert list(reactors_for_path([reactor_a, reactor_b, reactor_c], path_to_tuple("a"))) == [reactor_a, reactor_b, reactor_c]
    assert list(reactors_for_path([reactor_a, reactor_b, reactor_c], path_to_tuple("b"))) == [reactor_b, reactor_c]
    assert list(reactors_for_path([reactor_a, reactor_b, reactor_c], path_to_tuple("c"))) == [reactor_b, reactor_c]
    assert list(reactors_for_path([reactor_a, reactor_b, reactor_c], path_to_tuple("a/b/c"))) == [reactor_a, reactor_b, reactor_c]
