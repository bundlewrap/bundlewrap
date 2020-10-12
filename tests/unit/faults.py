from bundlewrap.utils import Fault

from pytest import raises


def test_basic_resolve():
    def callback():
        return 4  # Chosen by fair dice roll. Guaranteed to be random.

    f = Fault('id', callback)
    assert f.value == 4


def test_add_fault():
    def callback_a():
        return 'foo'
    def callback_b():
        return 'bar'

    a = Fault('id foo', callback_a)
    b = Fault('id bar', callback_b)
    c = a + b
    assert c.value == 'foobar'


def test_add_fault_nonstring():
    def callback_a():
        return 4
    def callback_b():
        return 8

    a = Fault('id foo', callback_a)
    b = Fault('id bar', callback_b)
    c = a + b
    assert c.value == 12


def test_add_plain_nonstring():
    def callback():
        return 4

    a = Fault('id foo', callback)
    b = a + 8
    assert b.value == 12


def test_add_plain():
    def callback_a():
        return 'foo'

    a = Fault('id foo', callback_a)
    c = a + 'bar'
    assert c.value == 'foobar'


def test_order():
    def callback_a():
        return 'foo'
    def callback_b():
        return 'bar'
    def callback_c():
        return '0first'

    a = Fault('id foo', callback_a)
    b = Fault('id bar', callback_b)
    c = Fault('id 0first', callback_c)

    lst = sorted([a, b, c])

    assert lst[0].value == '0first'
    assert lst[1].value == 'bar'
    assert lst[2].value == 'foo'


def test_b64encode():
    def callback():
        return 'foo'

    a = Fault('id foo', callback).b64encode()
    assert a.value == 'Zm9v'


def test_format_into():
    def callback():
        return 'foo'

    a = Fault('id foo', callback).format_into('This is my secret: "{}"')
    assert a.value == 'This is my secret: "foo"'


# XXX Other methods missing. This basically tests if
# _make_method_callback() is working.
def test_generic_method_lower():
    def callback():
        return 'FOO'

    a = Fault('id FOO', callback)
    assert a.lower().value == 'foo'


def test_equal_no_operators():
    def callback_a():
        return 'foo'
    def callback_b():
        return 'foo, but here you see the problem'

    a = Fault('id foo', callback_a)
    b = Fault('id foo', callback_b)
    assert id(a) != id(b)
    assert a == b


def test_not_equal_no_operators():
    def callback_a():
        return 'this interface is not fool proof'
    def callback_b():
        return 'this interface is not fool proof'

    a = Fault('id foo', callback_a)
    b = Fault('id bar', callback_b)
    assert id(a) != id(b)
    assert a != b


def test_equal_lower():
    def callback_a():
        return 'foo'
    def callback_b():
        return 'foo'

    a = Fault('id foo', callback_a).lower()
    b = Fault('id foo', callback_b).lower()
    assert id(a) != id(b)
    assert a == b


def test_not_equal_lower():
    def callback_a():
        return 'foo'
    def callback_b():
        return 'foo'

    a = Fault('id foo', callback_a).lower()
    b = Fault('id bar', callback_b).lower()
    assert id(a) != id(b)
    assert a != b


def test_equal_b64encode():
    def callback_a():
        return 'foo'
    def callback_b():
        return 'foo'

    a = Fault('id foo', callback_a).b64encode()
    b = Fault('id foo', callback_b).b64encode()
    assert id(a) != id(b)
    assert a == b


def test_not_equal_b64encode():
    def callback_a():
        return 'foo'
    def callback_b():
        return 'foo'

    a = Fault('id foo', callback_a).b64encode()
    b = Fault('id bar', callback_b).b64encode()
    assert id(a) != id(b)
    assert a != b


def test_equal_format_into():
    def callback_a():
        return 'foo'
    def callback_b():
        return 'foo'

    a = Fault('id foo', callback_a).format_into('bar {}')
    b = Fault('id foo', callback_b).format_into('bar {}')
    assert id(a) != id(b)
    assert a == b


def test_not_equal_format_into():
    def callback_a():
        return 'foo'
    def callback_b():
        return 'foo'

    a = Fault('id foo', callback_a).format_into('bar {}')
    b = Fault('id foo', callback_b).format_into('baz {}')
    assert id(a) != id(b)
    assert a != b


def test_nested_equal():
    def callback_a():
        return 'foo'
    def callback_b():
        return 'foo'

    a = Fault('id foo', callback_a).lower().b64encode()
    b = Fault('id foo', callback_b).lower().b64encode()
    assert id(a) != id(b)
    assert a == b


def test_nested_not_equal_because_of_id():
    def callback_a():
        return 'foo'
    def callback_b():
        return 'foo'

    a = Fault('id foo', callback_a).lower().b64encode()
    b = Fault('id bar', callback_b).lower().b64encode()
    assert id(a) != id(b)
    assert a != b


def test_nested_not_equal_because_of_operators():
    def callback_a():
        return 'foo'
    def callback_b():
        return 'foo'

    a = Fault('id foo', callback_a).lower().b64encode()
    b = Fault('id foo', callback_b).lower()
    assert id(a) != id(b)
    assert a != b


def test_can_be_used_in_set():
    def callback_a():
        return 'foo'
    def callback_b():
        return 'bar'

    a = Fault('id foo', callback_a)
    b = Fault('id bar', callback_b)
    s = {a, a, b}
    assert len(s) == 2
    assert 'foo' in [i.value for i in s]
    assert 'bar' in [i.value for i in s]


def test_kwargs_add_to_idlist():
    def callback():
        return 'foo'

    a = Fault('id foo', callback, foo='bar', baz='bam', frob='glob')
    b = Fault('id foo', callback, different='kwargs')
    assert a != b
    assert hash(a) != hash(b)


def test_unhashable_dict_kwargs_add_to_idlist():
    def callback():
        return 'foo'

    a = Fault('id foo', callback, foo='bar', baz={1: {2: {3: 4}}})
    b = Fault('id foo', callback, foo='bar', baz={1: {3: {3: 4}}})
    assert a != b
    assert hash(a) != hash(b)


def test_unhashable_list_kwargs_add_to_idlist():
    def callback():
        return 'foo'

    a = Fault('id foo', callback, foo='bar', baz=[1, 2, [3, 4]])
    b = Fault('id foo', callback, foo='bar', baz=[1, [3, 4], 2])
    assert a != b
    assert hash(a) != hash(b)


def test_unhashable_set_kwargs_add_to_idlist():
    def callback():
        return 'foo'

    a = Fault('id foo', callback, foo='bar', baz={1, 2, 3})
    b = Fault('id foo', callback, foo='bar', baz={1, 2, 4})
    assert a != b
    assert hash(a) != hash(b)


def test_unhashable_dict_kwargs_add_to_idlist_equal():
    def callback():
        return 'foo'

    a = Fault('id foo', callback, foo='bar', baz={1: {2: {3: 4, 5: 6}}})
    b = Fault('id foo', callback, foo='bar', baz={1: {2: {5: 6, 3: 4}}})
    assert a == b
    assert hash(a) == hash(b)


def test_unhashable_list_kwargs_add_to_idlist_equal():
    def callback():
        return 'foo'

    a = Fault('id foo', callback, foo='bar', baz=[1, 2, 3])
    b = Fault('id foo', callback, foo='bar', baz=[1, 2, 3])
    assert id(a) != id(b)
    assert a == b


def test_unhashable_set_kwargs_add_to_idlist_equal():
    def callback():
        return 'foo'

    a = Fault('id foo', callback, foo='bar', baz={1, 2, 3})
    b = Fault('id foo', callback, foo='bar', baz={1, 3, 2})
    assert a == b
    assert hash(a) == hash(b)


def test_eq_and_hash_do_not_resolve_fault():
    def callback():
        raise Exception('Fault resolved, this should not happen')

    a = Fault('id foo', callback)
    b = Fault('id foo', callback)
    assert a == b

    s = {a, b}


def test_kwargs_changed_after_creation():
    def callback():
        return 'foo'

    data = {
        'foo': 0,
    }
    a = Fault('id foo', callback, data=data)

    data['foo'] = 1
    b = Fault('id foo', callback, data=data)

    # Even though both Faults reference the same dict, hashes are built
    # on Fault creation based on the actual values in mutable
    # parameters.
    assert a != b
    assert hash(a) != hash(b)


def test_kwargs_not_changed_after_creation():
    def callback():
        return 'foo'

    data = {
        'foo': 0,
    }
    a = Fault('id foo', callback, data=data)
    b = Fault('id foo', callback, data=data)

    assert a == b
    assert hash(a) == hash(b)


def test_hash_does_not_change():
    def callback():
        return 'foo'

    data = {
        'foo': 0,
    }
    a = Fault('id foo', callback, data=data)
    hash1 = hash(a)

    data['foo'] = 1
    hash2 = hash(a)

    assert hash1 == hash2


def test_sort():
    def one():
        return 1

    def three():
        return 3

    f1 = Fault("1", one)
    f3 = Fault("3", three)

    assert sorted([2, f3, f1]) == [f1, 2, f3]


def test_sort_typeerror():
    def one():
        return 1

    def three():
        return 3

    f1 = Fault("1", one)
    f3 = Fault("3", three)

    with raises(TypeError):
        sorted(["2", f3, f1])


def test_sort_typeerror_from_fault():
    def one():
        return 1

    def three():
        return "3"

    f1 = Fault("1", one)
    f3 = Fault("3", three)

    with raises(TypeError):
        sorted([2, f3, f1])
