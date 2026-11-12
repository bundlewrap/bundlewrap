from random import Random

from bundlewrap.metagen import PathSet


def _reference_covers(paths, candidate):
    return any(candidate[:len(path)] == path for path in paths)


def _reference_add(paths, new_path):
    if _reference_covers(paths, new_path):
        return False
    for path in list(paths):
        if path[:len(new_path)] == new_path:
            paths.remove(path)
    paths.add(new_path)
    return True


def test_keeps_highest_level():
    s = PathSet()
    assert s.add(("foo", "bar"))
    assert s.add(("foo",))
    assert set(s) == {("foo",)}
    assert not s.add(("foo", "baz"))
    assert set(s) == {("foo",)}


def test_covers():
    s = PathSet([("a", "b"), ("c",)])
    assert s.covers(("a", "b"))
    assert s.covers(("a", "b", "x"))
    assert s.covers(("c", "d"))
    assert not s.covers(("a",))
    assert not s.covers(())
    assert not s.covers(("a", "c"))
    assert not s.covers(("x",))


def test_empty_path_covers_everything():
    s = PathSet([("a", "b"), ("c",)])
    assert s.add(())
    assert set(s) == {()}
    assert len(s) == 1
    assert s.covers(("a",))
    assert s.covers(())
    assert not s.add(("z",))


def test_add_removes_nested_paths():
    s = PathSet([("a", "b", "c"), ("a", "b", "d", "e"), ("a", "x")])
    assert s.add(("a", "b"))
    assert set(s) == {("a", "b"), ("a", "x")}
    assert len(s) == 2


def test_matches_reference_implementation():
    rnd = Random(42)
    keys = ("a", "b", "c", "d")
    for _ in range(200):
        s = PathSet()
        reference = set()
        for _ in range(60):
            path = tuple(rnd.choice(keys) for _ in range(rnd.choice((0,) + (1, 2, 3, 4) * 10)))
            if rnd.random() < 0.5:
                assert s.covers(path) == _reference_covers(reference, path)
            else:
                assert s.add(path) == _reference_add(reference, path)
            assert set(s) == reference
            assert len(s) == len(reference)
