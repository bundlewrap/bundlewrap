from bundlewrap.utils import Fault


def test_basic_resolve():
    def callback():
        return 4  # Chosen by fair dice roll. Guaranteed to be random.

    f = Fault(callback)
    assert f.value == 4


def test_add_fault():
    def callback_a():
        return 'foo'
    def callback_b():
        return 'bar'

    a = Fault(callback_a)
    b = Fault(callback_b)
    c = a + b
    assert c.value == 'foobar'


def test_add_plain():
    def callback_a():
        return 'foo'

    a = Fault(callback_a)
    c = a + 'bar'
    assert c.value == 'foobar'


def test_order():
    def callback_a():
        return 'foo'
    def callback_b():
        return 'bar'
    def callback_c():
        return '0first'

    a = Fault(callback_a)
    b = Fault(callback_b)
    c = Fault(callback_c)

    lst = sorted([a, b, c])

    assert lst[0].value == '0first'
    assert lst[1].value == 'bar'
    assert lst[2].value == 'foo'


def test_base64():
    def callback():
        return 'foo'

    a = Fault(callback).b64encode()
    assert a.value == 'Zm9v'


def test_format_into():
    def callback():
        return 'foo'

    a = Fault(callback).format_into('This is my secret: "{}"')
    assert a.value == 'This is my secret: "foo"'


# XXX Other methods missing. This basically tests if
# _make_method_callback() is working.
def test_generic_method_lower():
    def callback():
        return 'FOO'

    a = Fault(callback)
    assert a.lower().value == 'foo'
