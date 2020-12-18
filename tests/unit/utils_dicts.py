from bundlewrap.metadata import atomic
from bundlewrap.utils.dicts import (
    extra_paths_in_dict,
    map_dict_keys,
    reduce_dict,
    validate_dict,
    COLLECTION_OF_STRINGS,
    TUPLE_OF_INTS,
)

from pytest import raises


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


def test_validate_ok():
    validate_dict(
        {
            'a': 5,
            'b': "bee",
            'c': None,
            'd': ("t", "u", "p", "l", "e"),
            'e': ["l", "i", "s", "t"],
            'f': {"s", "e", "t"},
            'g': (1, "2"),
            'h': [1, "2"],
            'i': {1, "2"},
            'j': True,
            'k': False,
            'l': (1, 2, 3),
        },
        {
            'a': int,
            'b': str,
            'c': type(None),
            'd': COLLECTION_OF_STRINGS,
            'e': COLLECTION_OF_STRINGS,
            'f': COLLECTION_OF_STRINGS,
            'g': tuple,
            'h': list,
            'i': set,
            'j': bool,
            'k': (int, bool),
            'l': TUPLE_OF_INTS,
        },
    )


def test_validate_single_type_error():
    with raises(ValueError):
        validate_dict(
            {
                'a': 5,
            },
            {
                'a': str,
            },
        )


def test_validate_multi_type_error():
    with raises(ValueError):
        validate_dict(
            {
                'a': 5,
            },
            {
                'a': (str, list),
            },
        )


def test_validate_inner_type_error():
    with raises(ValueError):
        validate_dict(
            {
                'd': ("t", "u", "p", "l", "e", 47),
            },
            {
                'd': COLLECTION_OF_STRINGS,
            },
        )


def test_validate_inner_type_error2():
    with raises(ValueError):
        validate_dict(
            {
                'l': (1, 2, "3"),
            },
            {
                'l': TUPLE_OF_INTS,
            },
        )


def test_validate_missing_key():
    with raises(ValueError):
        validate_dict(
            {
                'a': 5,
            },
            {
                'a': int,
                'b': str,
            },
            required_keys=['a', 'b'],
        )


def test_validate_required_key():
    validate_dict(
        {
            'a': 5,
            'b': "bee",
        },
        {
            'a': int,
            'b': str,
        },
        required_keys=['a', 'b'],
    )


def test_extra_paths():
    assert set(extra_paths_in_dict(
        {
            'a': 1,
            'b': 1,
        },
        {
            ('a',),
        },
    )) == {
        ('b',),
    }


def test_extra_paths_nested():
    assert set(extra_paths_in_dict(
        {
            'a': 1,
            'b': {
                'c': 1
            },
            'd': {
                'e': 1
            },
        },
        {
            ('b', 'c'),
        },
    )) == {
        ('a',),
        ('d',),
        ('d', 'e'),
    }


def test_extra_paths_ok():
    assert set(extra_paths_in_dict(
        {
            'a': 1,
            'b': {
                'c': 1
            },
            'd': {
                'e': 1
            },
        },
        {
            ('a',),
            ('b', 'c'),
            ('d',),
        },
    )) == set()
