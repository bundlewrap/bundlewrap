from bundlewrap.utils import Fault


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
