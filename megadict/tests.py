from pytest import raises

from bundlewrap.metadata import atomic

from megadict import MegaDictNode, MegaDictCallback


def test_empty():
    m = MegaDictNode()
    assert m.get() == {}


def test_keyerror():
    m = MegaDictNode()
    with raises(KeyError):
        m.get(('foo',))


def test_keyerror_nested():
    m = MegaDictNode()
    m.add({'foo': {'bar': 47}})
    with raises(KeyError):
        m.get(('foo', 'baz'))


def test_add_and_get_value():
    m = MegaDictNode()
    m.add({'foo': {'bar': 47}})
    assert m.get(('foo', 'bar')) == 47


def test_add_and_get_dict():
    m = MegaDictNode()
    m.add({'foo': {'bar': 47}})
    assert m.get(('foo',)) == {'bar': 47}


def test_path_root():
    m = MegaDictNode()
    assert m.path == ()


def test_path():
    m = MegaDictNode()
    m.add({'foo': {'bar': 47}})
    assert m.get_node(('foo', 'bar')).path == ('foo', 'bar')


def test_layering():
    m = MegaDictNode()
    m.add({'foo': {'bar': 42}}, layer=1)
    assert m.get(('foo', 'bar')) == 42
    m.add({'foo': {'bar': 47}}, layer=0)
    assert m.get(('foo', 'bar')) == 47
    m.add({'foo': {'bar': 23}}, layer=2)
    assert m.get(('foo', 'bar')) == 47


def test_layering_atomic():
    m = MegaDictNode()
    m.add({'foo': {'bar': 42}}, layer=1)
    m.add({'foo': atomic({'baz': 47})}, layer=0)
    assert m.get(('foo',)) == {'baz': 47}


def test_merging_no_conflict():
    m = MegaDictNode()
    m.add({'foo': 47}, source='1')
    m.add({'bar': 23}, source='2')
    assert m.get() == {'foo': 47, 'bar': 23}


def test_merging_int_conflict():
    m = MegaDictNode()
    m.add({'foo': 47}, source='1')
    m.add({'foo': 23}, source='2')
    with raises(ValueError):
        print(m.get())


def test_merging_nested_conflict():
    m = MegaDictNode()
    m.add({'foo': 47}, source='1')
    m.add({'foo': {'bar': 23}}, source='2')
    with raises(ValueError):
        print(m.get())


def test_merging_int_conflict_resolved_by_layer():
    m = MegaDictNode()
    m.add({'foo': 47}, source='1', layer=0)
    m.add({'foo': 23}, source='2', layer=1)
    assert m.get(('foo',)) == 47


def test_merging_dict_no_conflict():
    m = MegaDictNode()
    m.add({'foo': {'bar': 47}}, source='1')
    m.add({'foo': {'baz': 23}}, source='2')
    assert m.get() == {'foo': {'bar': 47, 'baz': 23}}


def test_merging_dict_atomic_conflict():
    m = MegaDictNode()
    m.add({'foo': atomic({'bar': 47})}, source='1')
    m.add({'foo': atomic({'baz': 23})}, source='2')
    with raises(ValueError):
        print(m.get())


def test_merging_dict_atomic_conflict_mixed():
    m = MegaDictNode()
    m.add({'foo': {'bar': 47}}, source='1')
    m.add({'foo': atomic({'baz': 23})}, source='2')
    with raises(ValueError):
        print(m.get())


def test_merging_dict_int_conflict():
    m = MegaDictNode()
    m.add({'foo': {'bar': 47}}, source='1')
    m.add({'foo': 23}, source='2')
    with raises(ValueError):
        print(m.get())


def test_merging_dict_layered():
    m = MegaDictNode()
    m.add({'foo': {'bar': 47}, 'frob': 69}, source='1', layer=0)
    m.add({'foo': {'bar': 23}, 'baz': 42}, source='2', layer=1)
    assert m.get() == {
        'foo': {
            'bar': 47,
        },
        'baz': 42,
        'frob': 69,
    }


def test_remove():
    m = MegaDictNode()
    m.add({'foo': {'bar': 47}}, layer=1, source='1')
    m.add({'foo': {'bar': 42}}, layer=0, source='0')
    m.remove(0, '0')
    assert m.get(('foo', 'bar')) == 47


def test_blame():
    m = MegaDictNode()
    m.add({'foo': {'bar': 47}, 'frob': 69}, source='1', layer=0)
    m.add({'foo': {'bar': 23}, 'baz': 42}, source='2', layer=1)
    assert m.get_node(('foo',)).value_and_blame[1] == {'1'}
    assert m.get_node(('foo', 'bar')).value_and_blame[1] == {'1'}
    assert m.get_node(('baz',)).value_and_blame[1] == {'2'}


def test_callback():
    m = MegaDictNode()
    c = MegaDictCallback(m, 'c', 0, lambda m: {'foo': 47})
    m.add_callback_for_path(('foo',), c)
    assert m.get() == {'foo': 47}
    assert m.get(('foo',)) == 47


def test_callback_conflict():
    m = MegaDictNode()
    c1 = MegaDictCallback(m, 'c1', 0, lambda m: {'foo': 47})
    c2 = MegaDictCallback(m, 'c2', 0, lambda m: {'foo': {'bar': 47}})
    m.add_callback_for_path(('foo',), c1)
    m.add_callback_for_path(('foo', 'bar'), c2)
    with raises(ValueError):
        print(m.get())


def test_callback_blame():
    m = MegaDictNode()
    c1 = MegaDictCallback(m, 'c1', 0, lambda m: {'foo': {'bar': {23}}})
    c2 = MegaDictCallback(m, 'c2', 0, lambda m: {'foo': {'bar': {47}}})
    m.add_callback_for_path(('foo',), c1)
    m.add_callback_for_path(('foo', 'bar'), c2)
    assert m.get_node(('foo', 'bar')).value_and_blame == ({23, 47}, {'c1', 'c2'})


def test_callback_blame_cross_layer():
    m = MegaDictNode()
    c1 = MegaDictCallback(m, 'c1', 0, lambda m: {'foo': {'bar': {23}}})
    c2 = MegaDictCallback(m, 'c2', 1, lambda m: {'foo': {'bar': {47}}})
    m.add_callback_for_path(('foo',), c1)
    m.add_callback_for_path(('foo', 'bar'), c2)
    print(m.get_node(('foo', 'bar')).layers)
    assert m.get_node(('foo', 'bar')).value_and_blame == ({23, 47}, {'c1', 'c2'})


def test_nested_callback():
    m = MegaDictNode()
    c1 = MegaDictCallback(m, 'c1', 0, lambda m: {'baz': m.get(('bar',)) + 1})
    c2 = MegaDictCallback(m, 'c2', 0, lambda m: {'bar': m.get(('foo',)) + 1})
    c3 = MegaDictCallback(m, 'c3', 0, lambda m: {'foo': 47})
    m.add_callback_for_path(('baz',), c1)
    m.add_callback_for_path(('bar',), c2)
    m.add_callback_for_path(('foo',), c3)
    assert m.get(('baz',)) == 49


def test_lazy_callback():
    m = MegaDictNode()
    c1 = MegaDictCallback(m, 'c1', 0, lambda m: {'baz': 0 / 0})
    c2 = MegaDictCallback(m, 'c2', 0, lambda m: {'bar': m.get(('foo',)) + 1})
    c3 = MegaDictCallback(m, 'c3', 0, lambda m: {'foo': 47})
    m.add_callback_for_path(('baz',), c1)
    m.add_callback_for_path(('bar',), c2)
    m.add_callback_for_path(('foo',), c3)
    assert m.get(('bar',)) == 48


def test_lazy_callback_layers():
    m = MegaDictNode()
    c1 = MegaDictCallback(m, 'c1', 1, lambda m: {'bar': 0 / 0})
    c2 = MegaDictCallback(m, 'c2', 0, lambda m: {'bar': m.get(('foo',)) + 1})
    c3 = MegaDictCallback(m, 'c3', 0, lambda m: {'foo': 47})
    m.add_callback_for_path(('bar',), c1)
    m.add_callback_for_path(('bar',), c2)
    m.add_callback_for_path(('foo',), c3)
    assert m.get(('bar',)) == 48


def test_lazy_keys():
    m = MegaDictNode()
    c1 = MegaDictCallback(m, 'c1', 0, lambda m: {'foo': {'bar': 1}})
    c2 = MegaDictCallback(m, 'c2', 0, lambda m: {'foo': {'bar': 2}})
    m.add_callback_for_path(('foo', 'bar',), c1)
    m.add_callback_for_path(('foo', 'bar',), c2)

    # these do not raise ValueError, because they're not supposed to
    # merge the values
    assert sorted(m.keys()) == ['foo']
    assert sorted(m.keys(('foo',))) == ['bar']

    with raises(ValueError):
        print(m.get())
