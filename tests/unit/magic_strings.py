from pytest import raises

from bundlewrap.exceptions import InvalidMagicStringException
from bundlewrap.metadata import atomic
from bundlewrap.repo import Repository
from bundlewrap.utils import Fault
from bundlewrap.utils.dicts import _Atomic
from bundlewrap.utils.magic_strings import convert_magic_strings


def _magic_str(string):
    return string


def _magic_fault(string):
    return Fault("magic fault", lambda: string)


def _make_repo(add_magic_string_functions):
    repo = Repository()
    if add_magic_string_functions:
        repo.magic_string_functions = {
            "str": _magic_str,
            "fault": _magic_fault,
        }
    return repo


def test_passthrough_unchanged_no_functions():
    repo = _make_repo(False)

    metadata = {
        "a dict": {
            "has": "strings",
            "and": ["lists"],
            "and also": {"sets"},
        }
    }
    converted = convert_magic_strings(repo, metadata)
    assert converted == metadata


def test_passthrough_unchanged_with_functions():
    repo = _make_repo(True)

    metadata = {
        "a dict": {
            "has": "strings",
            "and": ["lists"],
            "and also": {"sets"},
        }
    }
    converted = convert_magic_strings(repo, metadata)
    assert converted == metadata


def test_magic_to_string():
    repo = _make_repo(True)

    metadata = {"a string": "!str:foo"}
    converted = convert_magic_strings(repo, metadata)
    assert converted["a string"] == "foo"


def test_magic_to_fault():
    repo = _make_repo(True)

    metadata = {"a string": "!fault:foo"}
    converted = convert_magic_strings(repo, metadata)
    assert isinstance(converted["a string"], Fault)
    assert converted["a string"].value == "foo"


def test_invalid_magic_string():
    repo = _make_repo(True)

    metadata = {"a string": "!nonexist:foo"}
    with raises(InvalidMagicStringException):
        convert_magic_strings(repo, metadata)


def test_supports_atomic():
    repo = _make_repo(True)

    metadata = {
        "a dict": atomic(
            {
                "a string": "!str:foo",
            }
        )
    }
    converted = convert_magic_strings(repo, metadata)
    assert isinstance(converted["a dict"], _Atomic)
    assert isinstance(converted["a dict"], dict)
    assert converted["a dict"]["a string"] == "foo"


def _magic_node(string, node=None):
    return "{}@{}".format(string, node.name if node else "no node")


def _magic_kwargs(string, **kwargs):
    return "{}@{}".format(string, kwargs['node'].name if 'node' in kwargs else "no node")


def _make_node_repo():
    repo = _make_repo(True)
    repo.magic_string_functions["node"] = _magic_node
    repo.magic_string_functions["kwargs"] = _magic_kwargs
    return repo


class _FakeNode:
    name = "node1"


def test_empty_argument():
    repo = _make_repo(True)

    metadata = {"a string": "!str:"}
    converted = convert_magic_strings(repo, metadata)
    assert converted["a string"] == ""


def test_node_passed_only_to_functions_that_accept_it():
    repo = _make_node_repo()

    metadata = {
        "plain": "!str:foo",
        "node": "!node:foo",
        "kwargs": "!kwargs:foo",
        "nested": ["!node:bar"],
    }
    converted = convert_magic_strings(repo, metadata, node=_FakeNode())
    assert converted["plain"] == "foo"
    assert converted["node"] == "foo@node1"
    assert converted["kwargs"] == "foo@node1"
    assert converted["nested"] == ["bar@node1"]


def test_node_not_passed_when_absent():
    repo = _make_node_repo()

    metadata = {"node": "!node:foo", "kwargs": "!kwargs:foo"}
    converted = convert_magic_strings(repo, metadata)
    assert converted["node"] == "foo@no node"
    assert converted["kwargs"] == "foo@no node"


def test_accepts_node():
    from functools import partial, wraps

    from bundlewrap.utils.magic_strings import _accepts_node

    def plain(string):
        return string

    def with_node(string, node=None):
        return string

    def with_kwargs(string, **kwargs):
        return string

    def positional_only(string, node, /):
        return string

    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            return func(*args, **kwargs)
        return wrapper

    def bare_decorator(func):
        def wrapper(string):
            return func(string)
        return wrapper

    class Callable:
        def __call__(self, string, node=None):
            return string

    class Unhashable:
        __hash__ = None

        def __call__(self, string, node=None):
            return string

    assert _accepts_node(plain) is False
    assert _accepts_node(with_node) is True
    assert _accepts_node(with_kwargs) is True
    assert _accepts_node(positional_only) is False
    assert _accepts_node(decorator(with_node)) is True
    assert _accepts_node(bare_decorator(with_node)) is False
    assert _accepts_node(partial(with_node, node="x")) is True
    assert _accepts_node(Callable()) is True
    assert _accepts_node(Unhashable()) is False
    assert _accepts_node(len) is False
