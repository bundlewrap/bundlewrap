from bundlewrap.utils.metastack import Metastack
from pytest import raises


def test_has_no_top():
    stack = Metastack()
    assert stack.has('something') == False


def test_has_no_subpath():
    stack = Metastack()
    stack._set_layer('identifier', {'something': {'in': {}}})
    assert stack.has('something/in/a/path') == False


def test_has_top():
    stack = Metastack()
    stack._set_layer('identifier', {'something': 123})
    assert stack.has('something') == True


def test_get_top():
    stack = Metastack()
    stack._set_layer('identifier', {'something': 123})
    assert stack.get('something', None) == 123


def test_has_subpath():
    stack = Metastack()
    stack._set_layer('identifier', {'something': {'in': {'a': 'subpath'}}})
    assert stack.has('something/in/a') == True


def test_get_subpath():
    stack = Metastack()
    stack._set_layer('identifier', {'something': {'in': {'a': 'subpath'}}})
    assert stack.get('something/in/a', None) == 'subpath'


def test_has_with_base():
    stack = Metastack({'something': {'a_list': [1, 2], 'a_value': 5}})
    assert stack.has('something/a_list') == True
    assert stack.has('something/a_value') == True
    assert stack.has('something/does_not_exist') == False


def test_get_default_with_empty():
    stack = Metastack()
    assert stack.get('something', 123) == 123


def test_get_default_with_base():
    stack = Metastack({'foo': 'bar'})
    assert stack.get('something', 123) == 123


def test_get_default_with_overlay():
    stack = Metastack({'foo': 'bar'})
    stack._set_layer('identifier', {'baz': 'boing'})
    assert stack.get('something', 123) == 123


def test_overlay_value():
    stack = Metastack({'something': {'a_list': [1, 2], 'a_value': 5}})
    stack._set_layer('identifier', {'something': {'a_value': 10}})
    assert stack.get('something/a_value', None) == 10


def test_merge_lists():
    stack = Metastack({'something': {'a_list': [1, 2], 'a_value': 5}})
    stack._set_layer('identifier', {'something': {'a_list': [3]}})
    assert sorted(stack.get('something/a_list', None)) == sorted([1, 2, 3])


def test_merge_sets():
    stack = Metastack({'something': {'a_set': {1, 2}, 'a_value': 5}})
    stack._set_layer('identifier', {'something': {'a_set': {3}}})
    assert stack.get('something/a_set', None) == {1, 2, 3}


def test_overlay_value_multi_layers():
    stack = Metastack({'something': {'a_list': [1, 2], 'a_value': 5}})
    stack._set_layer('identifier', {'something': {'a_value': 10}})
    stack._set_layer('unrelated', {'something': {'another_value': 10}})
    assert stack.get('something/a_value', None) == 10


def test_merge_lists_multi_layers():
    stack = Metastack({'something': {'a_list': [1, 2], 'a_value': 5}})
    stack._set_layer('identifier', {'something': {'a_list': [3]}})
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
    stack = Metastack({'something': {'a_set': {1, 2}, 'a_value': 5}})
    stack._set_layer('identifier', {'something': {'a_set': {3}}})
    stack._set_layer('unrelated', {'something': {'another_value': 10}})
    assert stack.get('something/a_set', None) == {1, 2, 3}


def test_merge_lists_with_empty_layer():
    stack = Metastack({'something': {'a_list': [1, 2], 'a_value': 5}})
    stack._set_layer('identifier1', {'something': {'a_list': []}})
    stack._set_layer('identifier2', {'something': {'a_list': [3]}})
    assert sorted(stack.get('something/a_list', None)) == sorted([1, 2, 3])


def test_merge_sets_with_empty_layer():
    stack = Metastack({'something': {'a_set': {1, 2}, 'a_value': 5}})
    stack._set_layer('identifier1', {'something': {'a_set': set()}})
    stack._set_layer('identifier2', {'something': {'a_set': {3}}})
    assert stack.get('something/a_set', None) == {1, 2, 3}


def test_merge_lists_with_multiple_used_layers():
    stack = Metastack({'something': {'a_list': [1, 2], 'a_value': 5}})
    stack._set_layer('identifier1', {'something': {'a_list': [3]}})
    stack._set_layer('identifier2', {'something': {'a_list': [4]}})
    stack._set_layer('identifier3', {'something': {'a_list': [6, 5]}})
    assert sorted(stack.get('something/a_list', None)) == sorted([1, 2, 3, 4, 5, 6])


def test_merge_sets_with_multiple_used_layers():
    stack = Metastack({'something': {'a_set': {1, 2}, 'a_value': 5}})
    stack._set_layer('identifier1', {'something': {'a_set': {3}}})
    stack._set_layer('identifier2', {'something': {'a_set': {4}}})
    stack._set_layer('identifier3', {'something': {'a_set': {6, 5}}})
    assert stack.get('something/a_set', None) == {1, 2, 3, 4, 5, 6}


def test_merge_dicts():
    stack = Metastack()
    stack._set_layer('identifier1', {'something': {'a_value': 3}})
    stack._set_layer('identifier2', {'something': {'another_value': 5}})
    stack._set_layer('identifier3', {'something': {'this': {'and': 'that'}}})
    stack._set_layer('identifier4', {'something': {'a_set': {1, 2}}})
    stack._set_layer('identifier5', {'something': {'a_set': {3, 4}}})
    assert stack.get('something', None) == {
        'a_set': {1, 2, 3, 4},
        'a_value': 3,
        'another_value': 5,
        'this': {
            'and': 'that',
        },
    }


def test_requesting_empty_path():
    stack = Metastack({'foo': {'bar': 'baz'}})
    assert stack.get('', 'default') == 'default'


def test_update_layer_for_new_value():
    stack = Metastack({'foo': 'bar'})

    stack._set_layer('identifier', {'something': 123})
    assert stack.get('foo', None) == 'bar'
    assert stack.get('boing', 'default') == 'default'
    assert stack.get('something', None) == 123

    stack._set_layer('identifier', {'something': 456})
    assert stack.get('foo', None) == 'bar'
    assert stack.get('boing', 'default') == 'default'
    assert stack.get('something', None) == 456


def test_should_be_frozen():
    stack = Metastack({'foo': {'bar': {1, 2, 3}}})
    foo = stack.get('foo', None)

    with raises(AttributeError):
        foo['bar'].add(4)

    with raises(TypeError):
        del foo['bar']
