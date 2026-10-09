from bundlewrap.utils.dicts import merge_dict
from bundlewrap.metadata import atomic


def test_atomic_no_merge_base():
    assert merge_dict(
        {1: atomic([5])},
        {1: [6, 7]},
    ) == {1: [6, 7]}


def test_atomic_no_merge_update():
    assert merge_dict(
        {1: [5]},
        {1: atomic([6, 7])},
    ) == {1: [6, 7]}


def test_deepcopy_metadata():
    from bundlewrap.metadata import deepcopy_metadata
    from bundlewrap.utils.dicts import _AtomicDict, _AtomicList

    class MyStr(str):
        pass

    inner_list = [1, {"x": "y"}]
    original = {
        "dict": {"list": inner_list, "tuple": (1, [2]), "set": {3}},
        MyStr("custom_key"): None,
        "atomic_dict": _AtomicDict({"a": [1]}),
        "atomic_list": _AtomicList([{"b": 2}]),
    }
    copied = deepcopy_metadata(original)
    assert copied == original
    assert copied["dict"]["list"] is not inner_list
    assert copied["dict"]["list"][1] is not inner_list[1]
    assert copied["dict"]["tuple"][1] is not original["dict"]["tuple"][1]
    assert type(copied["atomic_dict"]) is _AtomicDict
    assert type(copied["atomic_list"]) is _AtomicList
    assert copied["atomic_dict"]["a"] is not original["atomic_dict"]["a"]
    assert [type(key) for key in copied] == [type(key) for key in original]
