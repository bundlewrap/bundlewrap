from bundlewrap.metadata import atomic
from bundlewrap.utils.dicts import map_dict_keys, reduce_dict


def test_dictmap():
    assert set(map_dict_keys({
        'key1': 1,
        'key2': {
            'key3': [3, 3, 3],
            'key4': atomic([4, 4, 4]),
            'key5': {
                'key6': "6",
            },
            'key7': set((7, 7, 7)),
        },
    })) == set([
        ("key1",),
        ("key2",),
        ("key2", "key3"),
        ("key2", "key4"),
        ("key2", "key5"),
        ("key2", "key5", "key6"),
        ("key2", "key7"),
    ])


def test_reduce_dict_two_lists():
    assert reduce_dict(
        [1, 2, 3],
        [1, 2],
    ) == [1, 2, 3]


def test_reduce_dict_list_and_dict():
    assert reduce_dict(
        [1, 2, 3],
        {'a': 4},
    ) == [1, 2, 3]


def test_reduce_dict_simple():
    assert reduce_dict(
        {'a': 1, 'b': 2},
        {'a': 3},
    ) == {'a': 1}


def test_reduce_dict_nested():
    full_dict = {
        'a': [{
            'b': 1,
            'c': 2,
        }],
        'd': 3,
    }
    template_dict = {
        'a': [{
            'b': None,
        }],
        'd': None,
        'e': None,
    }
    assert reduce_dict(full_dict, template_dict) == {
        'a': [{
            'b': 1,
        }],
        'd': 3,
    }
