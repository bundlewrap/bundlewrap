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
