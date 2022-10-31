from pytest import raises

from bundlewrap.metadata import atomic

from megadict import LazyTreeNode


def test_empty():
    m = LazyTreeNode()
    assert m.get() == {}


def test_keyerror():
    m = LazyTreeNode()
    with raises(KeyError):
        m.get('foo')


def test_keyerror_nested():
    m = LazyTreeNode()
    m.add_callback_for_paths({()}, lambda m: {'foo': {'bar': 47}})
    with raises(KeyError):
        m.get('foo/baz')


def test_add_and_get_value():
    m = LazyTreeNode()
    m.add_callback_for_paths({'foo'}, lambda m: {'foo': {'bar': 47}})
    assert m.get('foo/bar') == 47


def test_add_and_get_dict():
    m = LazyTreeNode()
    m.add_callback_for_paths({'foo'}, lambda m: {'foo': {'bar': 47}})
    assert m.get('foo') == {'bar': 47}


def test_path_root():
    m = LazyTreeNode()
    assert m.path == ()


def test_path():
    m = LazyTreeNode()
    assert m.get_node('foo/bar').path == ('foo', 'bar')


def test_layering():
    m = LazyTreeNode()
    m.add_callback_for_paths({'foo'}, lambda m: {'foo': {'bar': 42}}, layer=1)
    assert m.get('foo/bar') == 42
    m.add_callback_for_paths({'foo'}, lambda m: {'foo': {'bar': 47}}, layer=0)
    assert m.get('foo/bar') == 47
    m.add_callback_for_paths({'foo'}, lambda m: {'foo': {'bar': 23}}, layer=2)
    assert m.get('foo/bar') == 47


def test_layering_atomic():
    m = LazyTreeNode()
    m.add_callback_for_paths({'foo'}, lambda m: {'foo': {'bar': 42}}, layer=1)
    m.add_callback_for_paths({'foo'}, lambda m: {'foo': atomic({'baz': 47})}, layer=0)
    assert m.get('foo') == {'baz': 47}


def test_merging_no_conflict():
    m = LazyTreeNode()
    m.add_callback_for_paths({()}, lambda m: {'foo': 47})
    m.add_callback_for_paths({()}, lambda m: {'bar': 23})
    assert m.get() == {'foo': 47, 'bar': 23}


def test_merging_int_conflict():
    m = LazyTreeNode()
    m.add_callback_for_paths({()}, lambda m: {'foo': 47})
    m.add_callback_for_paths({()}, lambda m: {'foo': 23})
    with raises(ValueError):
        print(m.get())


def test_merging_nested_conflict():
    m = LazyTreeNode()
    m.add_callback_for_paths({()}, lambda m: {'foo': 47})
    m.add_callback_for_paths({()}, lambda m: {'foo': {'bar': 23}})
    with raises(ValueError):
        print(m.get())


def test_merging_int_conflict_resolved_by_layer():
    m = LazyTreeNode()
    m.add_callback_for_paths({()}, lambda m: {'foo': 47}, layer=0)
    m.add_callback_for_paths({()}, lambda m: {'foo': 23}, layer=1)
    assert m.get('foo') == 47


def test_merging_dict_no_conflict():
    m = LazyTreeNode()
    m.add_callback_for_paths({()}, lambda m: {'foo': {'bar': 47}})
    m.add_callback_for_paths({()}, lambda m: {'foo': {'baz': 23}})
    assert m.get() == {'foo': {'bar': 47, 'baz': 23}}


def test_merging_dict_atomic_conflict():
    m = LazyTreeNode()
    m.add_callback_for_paths({()}, lambda m: {'foo': atomic({'bar': 47})})
    m.add_callback_for_paths({()}, lambda m: {'foo': atomic({'baz': 23})})
    with raises(ValueError):
        print(m.get())


def test_merging_dict_atomic_conflict_mixed():
    m = LazyTreeNode()
    m.add_callback_for_paths({()}, lambda m: {'foo': {'bar': 47}})
    m.add_callback_for_paths({()}, lambda m: {'foo': atomic({'baz': 23})})
    with raises(ValueError):
        print(m.get())


def test_merging_dict_layered():
    m = LazyTreeNode()
    m.add_callback_for_paths({()}, lambda m: {'foo': {'bar': 47}, 'frob': 69}, layer=0)
    m.add_callback_for_paths({()}, lambda m: {'foo': {'bar': 23}, 'baz': 42}, layer=1)
    assert m.get() == {
        'foo': {
            'bar': 47,
        },
        'baz': 42,
        'frob': 69,
    }


def test_blame():
    m = LazyTreeNode()
    m.add_callback_for_paths({()}, lambda m: {'foo': {'bar': 47}, 'frob': 69}, layer=0, source='1')
    m.add_callback_for_paths({()}, lambda m: {'foo': {'bar': 23}, 'baz': 42}, layer=1, source='2')
    assert m.get_node(('foo',)).value_and_blame[1] == {'1'}
    assert m.get_node(('foo', 'bar')).value_and_blame[1] == {'1'}
    assert m.get_node(('baz',)).value_and_blame[1] == {'2'}


def test_blame_cross_layer():
    m = LazyTreeNode()
    m.add_callback_for_paths({()}, lambda m: {'foo': {'bar': {23}}}, layer=0, source='1')
    m.add_callback_for_paths({()}, lambda m: {'foo': {'bar': {47}}}, layer=1, source='2')
    assert m.get_node(('foo', 'bar')).value_and_blame == ({23, 47}, {'1', '2'})


def test_nested_callback():
    m = LazyTreeNode()
    m.add_callback_for_paths({'baz'}, lambda m: {'baz': m.get('bar') + 1})
    m.add_callback_for_paths({'bar'}, lambda m: {'bar': m.get(('foo',)) + 1})
    m.add_callback_for_paths({'foo'}, lambda m: {'foo': 47})
    assert m.get('baz') == 49


def test_lazy_callback():
    m = LazyTreeNode()
    m.add_callback_for_paths({'baz'}, lambda m: {'baz': 0 / 0})
    m.add_callback_for_paths({'bar'}, lambda m: {'bar': m.get(('foo',)) + 1})
    m.add_callback_for_paths({'foo'}, lambda m: {'foo': 47})
    assert m.get('bar') == 48


def test_lazy_callback_layers():
    m = LazyTreeNode()
    m.add_callback_for_paths({'bar'}, lambda m: {'bar': 0 / 0}, layer=1)
    m.add_callback_for_paths({'bar'}, lambda m: {'bar': m.get(('foo',)) + 1}, layer=0)
    m.add_callback_for_paths({'foo'}, lambda m: {'foo': 47}, layer=0)
    assert m.get('bar') == 48


def test_lazy_keys():
    m = LazyTreeNode()
    m.add_callback_for_paths({()}, lambda m: {'foo': {'bar': 1}})
    m.add_callback_for_paths({()}, lambda m: {'foo': {'bar': 2}})

    # these do not raise ValueError, because they're not supposed to
    # merge the values
    assert sorted(m.keys()) == ['foo']
    assert sorted(m.keys('foo')) == ['bar']

    with raises(ValueError):
        print(m.get())


def test_layer_link():
    m = LazyTreeNode()
    node1_metadata = m.get_node('node1/metadata')
    group1_metadata = m.get_node('group1/metadata')
    group2_metadata = m.get_node('group2/metadata')
    node1_metadata.add_callback_for_paths({()}, lambda m: {'foo': {23}, 'bar': 1}, layer=0)
    group1_metadata.add_callback_for_paths({()}, lambda m: {'foo': {47}, 'bar': 2}, layer=0)
    group2_metadata.add_callback_for_paths({()}, lambda m: {'foo': {42}, 'bar': 3, 'baz': None}, layer=0)
    node1_metadata.link(group1_metadata, 1)
    group1_metadata.link(group2_metadata, 1)
    assert m.get('node1/metadata') == {
        'foo': {23, 42, 47},
        'bar': 1,
        'baz': None,
    }
    assert m.get('group1/metadata/foo') == {42, 47}
    assert m.get('node1/metadata/baz') is None


def test_layer_link_blame():
    m = LazyTreeNode()
    node1_metadata = m.get_node('node1/metadata')
    group1_metadata = m.get_node('group1/metadata')
    group2_metadata = m.get_node('group2/metadata')
    node1_metadata.add_callback_for_paths({()}, lambda m: {'foo': {23}, 'bar': 1}, layer=0, source='node1')
    group1_metadata.add_callback_for_paths({()}, lambda m: {'foo': {47}, 'bar': 2}, layer=0, source='group1')
    group2_metadata.add_callback_for_paths({()}, lambda m: {'foo': {42}, 'bar': 3, 'baz': None}, layer=0, source='group2')
    node1_metadata.link(group1_metadata, 1)
    group1_metadata.link(group2_metadata, 1)
    assert m.get_node('node1/metadata/foo').blame == {'node1', 'group1', 'group2'}
    assert m.get_node('node1/metadata/bar').blame == {'node1'}
    assert m.get_node('node1/metadata/baz').blame == {'group2'}


def test_reentrant_callbacks():
    m = LazyTreeNode()
    m.add_callback_for_paths(
        {'foo', 'bar'},
        lambda m: {'foo': 1, 'bar': m.get('baz', None)},
    )
    m.add_callback_for_paths(
        {'baz'},
        lambda m: {'baz': m.get('foo', None)},
    )
    assert m.get('foo') == 1
    assert m.get('bar') == 1
    assert m.get('baz') == 1
