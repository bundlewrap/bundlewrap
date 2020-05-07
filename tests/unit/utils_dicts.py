from bundlewrap.metadata import atomic
from bundlewrap.utils.dicts import freeze_object, map_dict_keys, reduce_dict
from pytest import raises

from sys import version_info


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


def test_freeze_object():
    orig = {
        'bool': True,
        'int': 3,
        'none': None,
        'simple_list': [1, 2],
        'simple_set': {3, 4},
        'recursive_dict': {
            'something': {
                'else': 3,
            },
            'str': 'str',
        },
        'list_of_dicts': [
            {
                'name': 'yaml',
                'attribute': 123,
                'see': 'how lists of dicts are a bad idea anyway',
            },
            {
                'name': 'yaml',
                'attribute': 42,
                'everything': ['got', 'the', 'same', 'name'],
            },
        ],
    }

    frozen = freeze_object(orig)

    assert frozen['bool'] == True
    assert frozen['int'] == 3
    assert frozen['none'] == None
    assert frozen['simple_list'][0] == 1
    assert frozen['simple_list'][1] == 2
    assert len(frozen['simple_list']) == 2
    assert 4 in frozen['simple_set']
    assert len(frozen['simple_set']) == 2
    assert frozen['list_of_dicts'][0]['attribute'] == 123
    assert frozen['recursive_dict']['something']['else'] == 3

    # XXX Remove this if in bw 4.0 and always do the check
    if version_info[0] >= 3:
        with raises(TypeError):
            frozen['bool'] = False

        with raises(TypeError):
            frozen['int'] = 10

        with raises(TypeError):
            frozen['none'] = None

        with raises(TypeError):
            frozen['list_of_dicts'][0]['attribute'] = 456

        with raises(TypeError):
            frozen['recursive_dict']['something']['else'] = 4

        with raises(TypeError):
            del frozen['int']

    with raises(AttributeError):
        frozen['simple_list'].append(5)

    with raises(AttributeError):
        frozen['simple_set'].add(5)


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
