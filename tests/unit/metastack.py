from bundlewrap.metadata import atomic
from bundlewrap.utils.metastack import Metastack
from pytest import raises


def test_has_no_top():
    stack = Metastack()
    with raises(KeyError):
        stack.get('something')


def test_has_no_subpath():
    stack = Metastack()
    stack._set_layer('base', {'something': {'in': {}}})
    with raises(KeyError):
        stack.get('something/in/a/path')


def test_get_top():
    stack = Metastack()
    stack._set_layer('base', {'something': 123})
    assert stack.get('something') == 123


def test_get_subpath():
    stack = Metastack()
    stack._set_layer('base', {'something': {'in': {'a': 'subpath'}}})
    assert stack.get('something/in/a', None) == 'subpath'


def test_get_default_with_empty():
    stack = Metastack()
    assert stack.get('something', 123) == 123


def test_get_default_with_base():
    stack = Metastack()
    stack._set_layer('', {'foo': 'bar'})
    assert stack.get('something', 123) == 123


def test_get_default_with_overlay():
    stack = Metastack()
    stack._set_layer('base', {'foo': 'bar'})
    stack._set_layer('overlay', {'baz': 'boing'})
    assert stack.get('something', 123) == 123


def test_overlay_value():
    stack = Metastack()
    stack._set_layer('base', {'something': {'a_list': [1, 2], 'a_value': 5}})
    stack._set_layer('overlay', {'something': {'a_value': 10}})
    assert stack.get('something/a_value', None) == 10


def test_merge_lists():
    stack = Metastack()
    stack._set_layer('base', {'something': {'a_list': [1, 2], 'a_value': 5}})
    stack._set_layer('overlay', {'something': {'a_list': [3]}})
    assert sorted(stack.get('something/a_list', None)) == sorted([1, 2, 3])


def test_merge_sets():
    stack = Metastack()
    stack._set_layer('base', {'something': {'a_set': {1, 2}, 'a_value': 5}})
    stack._set_layer('overlay', {'something': {'a_set': {3}}})
    assert stack.get('something/a_set', None) == {1, 2, 3}


def test_overlay_value_multi_layers():
    stack = Metastack()
    stack._set_layer('base', {'something': {'a_list': [1, 2], 'a_value': 5}})
    stack._set_layer('overlay', {'something': {'a_value': 10}})
    stack._set_layer('unrelated', {'something': {'another_value': 10}})
    assert stack.get('something/a_value', None) == 10


def test_merge_lists_multi_layers():
    stack = Metastack()
    stack._set_layer('base', {'something': {'a_list': [1, 2], 'a_value': 5}})
    stack._set_layer('overlay', {'something': {'a_list': [3]}})
    stack._set_layer('unrelated', {'something': {'another_value': 10}})

    # Objects in Metastacks are frozen. This converts lists to tuples.
    # Unlike set and frozenset, list and tuple doesn't naturally support
    # "is equal".
    #
    # This is acceptable, because in metaprocs people are expected to
    # maybe check if something is in a list and maybe access some item
    # of a list. All that works. Operations like .append() do not work
    # and they are not supposed to.
    assert len(stack.get('something/a_list', None)) == 3
    assert stack.get('something/a_list', None)[0] == 1
    assert stack.get('something/a_list', None)[1] == 2
    assert stack.get('something/a_list', None)[2] == 3


def test_merge_sets_multi_layers():
    stack = Metastack()
    stack._set_layer('base', {'something': {'a_set': {1, 2}, 'a_value': 5}})
    stack._set_layer('overlay', {'something': {'a_set': {3}}})
    stack._set_layer('unrelated', {'something': {'another_value': 10}})
    assert stack.get('something/a_set', None) == {1, 2, 3}


def test_merge_lists_with_empty_layer():
    stack = Metastack()
    stack._set_layer('base', {'something': {'a_list': [1, 2], 'a_value': 5}})
    stack._set_layer('overlay1', {'something': {'a_list': []}})
    stack._set_layer('overlay2', {'something': {'a_list': [3]}})
    assert sorted(stack.get('something/a_list', None)) == sorted([1, 2, 3])


def test_merge_sets_with_empty_layer():
    stack = Metastack()
    stack._set_layer('base', {'something': {'a_set': {1, 2}, 'a_value': 5}})
    stack._set_layer('overlay1', {'something': {'a_set': set()}})
    stack._set_layer('overlay2', {'something': {'a_set': {3}}})
    assert stack.get('something/a_set', None) == {1, 2, 3}


def test_merge_lists_with_multiple_used_layers():
    stack = Metastack()
    stack._set_layer('base', {'something': {'a_list': [1, 2], 'a_value': 5}})
    stack._set_layer('overlay1', {'something': {'a_list': [3]}})
    stack._set_layer('overlay2', {'something': {'a_list': [4]}})
    stack._set_layer('overlay3', {'something': {'a_list': [6, 5]}})
    assert sorted(stack.get('something/a_list', None)) == sorted([1, 2, 3, 4, 5, 6])


def test_merge_sets_with_multiple_used_layers():
    stack = Metastack()
    stack._set_layer('base', {'something': {'a_set': {1, 2}, 'a_value': 5}})
    stack._set_layer('overlay1', {'something': {'a_set': {3}}})
    stack._set_layer('overlay2', {'something': {'a_set': {4}}})
    stack._set_layer('overlay3', {'something': {'a_set': {6, 5}}})
    assert stack.get('something/a_set', None) == {1, 2, 3, 4, 5, 6}


def test_merge_dicts():
    stack = Metastack()
    stack._set_layer('overlay1', {'something': {'a_value': 3}})
    stack._set_layer('overlay2', {'something': {'another_value': 5}})
    stack._set_layer('overlay3', {'something': {'this': {'and': 'that'}}})
    stack._set_layer('overlay4', {'something': {'a_set': {1, 2}}})
    stack._set_layer('overlay5', {'something': {'a_set': {3, 4}}})
    assert stack.get('something', None) == {
        'a_set': {1, 2, 3, 4},
        'a_value': 3,
        'another_value': 5,
        'this': {
            'and': 'that',
        },
    }


def test_requesting_empty_path():
    stack = Metastack()
    stack._set_layer('base', {'foo': {'bar': 'baz'}})
    assert stack.get('', 'default') == 'default'


def test_update_layer_for_new_value():
    stack = Metastack()
    stack._set_layer('base', {'foo': 'bar'})

    stack._set_layer('overlay', {'something': 123})
    assert stack.get('foo', None) == 'bar'
    assert stack.get('boing', 'default') == 'default'
    assert stack.get('something', None) == 123

    stack._set_layer('overlay', {'something': 456})
    assert stack.get('foo', None) == 'bar'
    assert stack.get('boing', 'default') == 'default'
    assert stack.get('something', None) == 456


def test_deepcopy():
    stack = Metastack()
    stack._set_layer('base', {'foo': {'bar': {1, 2, 3}}})
    foo = stack.get('foo', None)
    foo['bar'].add(4)
    assert stack.get('foo/bar') == {1, 2, 3}
    del foo['bar']
    assert stack.get('foo/bar')


def test_atomic_in_base():
    stack = Metastack()
    stack._set_layer('base', {'list': atomic([1, 2, 3])})
    stack._set_layer('overlay', {'list': [4]})
    assert list(stack.get('list', None)) == [4]


def test_atomic_in_layer():
    stack = Metastack()
    stack._set_layer('base', {'list': [1, 2, 3]})
    stack._set_layer('overlay', {'list': atomic([4])})
    assert list(stack.get('list', None)) == [4]


def test_set_layer_return_code():
    stack = Metastack()
    ret = stack._set_layer('overlay', {'foo': 'bar'})
    assert ret is True
    ret = stack._set_layer('overlay', {'foo': 'bar'})
    assert ret is False
    ret = stack._set_layer('overlay', {'foo': 'baz'})
    assert ret is True
    ret = stack._set_layer('overlay', {'foo': 'baz', 'bar': 1})
    assert ret is True


def test_as_dict():
    stack = Metastack()
    stack._set_layer('base', {
        'bool': True,
        'bytes': b'howdy',
        'dict': {'1': 2},
        'int': 1,
        'list': [1],
        'none': None,
        'set': {1},
        'str': 'howdy',
        'tuple': (1, 2),
    })
    stack._set_layer('overlay1', {'int': 1000})
    stack._set_layer('overlay2', {'list': [2]})
    stack._set_layer('overlay3', {'new_element': True})
    assert stack._as_dict() == {
        'bool': True,
        'bytes': b'howdy',
        'dict': {'1': 2},
        'int': 1000,
        'list': [1, 2],
        'new_element': True,
        'none': None,
        'set': {1},
        'str': 'howdy',
        'tuple': (1, 2),
    }


def test_as_blame():
    stack = Metastack()
    stack._set_layer('base', {'something': {'a_list': [1, 2], 'a_value': 5}})
    stack._set_layer('overlay', {'something': {'a_list': [3]}})
    stack._set_layer('unrelated', {'something': {'another_value': 10}})
    assert stack._as_blame() == {
        ('something',): ['base', 'overlay', 'unrelated'],
        ('something', 'a_list'): ['base', 'overlay'],
        ('something', 'a_value'): ['base'],
        ('something', 'another_value'): ['unrelated'],
    }
