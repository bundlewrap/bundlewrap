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
