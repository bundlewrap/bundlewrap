from bundlewrap.utils.table import ROW_SEPARATOR, render_table, _flatten_rows_with_lists


def test_render_table():
    assert "\n".join(render_table([
        ["head1", "h2"],
        ROW_SEPARATOR,
        ["1", "2"]
    ], alignments={0: 'right'})) == """
╭───────┬────╮
│ head1 │ h2 │
├───────┼────┤
│     1 │ 2  │
╰───────┴────╯
    """.strip()


def test_render_table_with_list():
    assert "\n".join(render_table([
        ["head1", "h2"],
        ROW_SEPARATOR,
        ["1", ["a", "b", "c"]]
    ], alignments={0: 'right'})) == """
╭───────┬────╮
│ head1 │ h2 │
├───────┼────┤
│     1 │ a  │
│       │ b  │
│       │ c  │
╰───────┴────╯
    """.strip()


def test_render_table_with_row_separator():
    assert "\n".join(render_table([
        ["head1", "h2"],
        ROW_SEPARATOR,
        ["1", "2"],
        ["3", "4"],
        ROW_SEPARATOR,
        ["5", "6"],
    ], alignments={0: 'right'})) == """
╭───────┬────╮
│ head1 │ h2 │
├───────┼────┤
│     1 │ 2  │
│     3 │ 4  │
├───────┼────┤
│     5 │ 6  │
╰───────┴────╯
    """.strip()


def test_render_table_with_inline_row_separator():
    assert "\n".join(render_table([
        ["h1", "h2", "h3"],
        ROW_SEPARATOR,
        ["1", "2", "3"],
        ["A", ROW_SEPARATOR, "B"],
        ["4", "5", "6"],
    ], alignments={0: 'right'})) == """
╭────┬────┬────╮
│ h1 │ h2 │ h3 │
├────┼────┼────┤
│  1 │ 2  │ 3  │
│  A ├────┤ B  │
│  4 │ 5  │ 6  │
╰────┴────┴────╯
    """.strip()


def test_render_table_with_emptylist():
    assert "\n".join(render_table([
        ["head1", "h2"],
        ROW_SEPARATOR,
        ["1", []]
    ], alignments={0: 'right'})) == """
╭───────┬────╮
│ head1 │ h2 │
├───────┼────┤
│     1 │ [] │
╰───────┴────╯
    """.strip()


def test_render_table_with_set():
    assert "\n".join(render_table([
        ["head1", "h2"],
        ROW_SEPARATOR,
        ["1", {"a", "b", "c"}]
    ], alignments={0: 'right'})) == """
╭───────┬────╮
│ head1 │ h2 │
├───────┼────┤
│     1 │ a  │
│       │ b  │
│       │ c  │
╰───────┴────╯
    """.strip()


def test_render_table_with_tuple():
    assert "\n".join(render_table([
        ["head1", "h2"],
        ROW_SEPARATOR,
        ["1", ("a", "b", "c")]
    ], alignments={0: 'right'})) == """
╭───────┬────╮
│ head1 │ h2 │
├───────┼────┤
│     1 │ a  │
│       │ b  │
│       │ c  │
╰───────┴────╯
    """.strip()


def test_render_table_with_multiple_lists():
    assert "\n".join(render_table([
        ["head1", "h2", "h2"],
        ROW_SEPARATOR,
        ["1", ["a", "b", "c"], ["Y", "Z"]]
    ], alignments={0: 'right'})) == """
╭───────┬────┬────╮
│ head1 │ h2 │ h2 │
├───────┼────┼────┤
│     1 │ a  │ Y  │
│       │ b  │ Z  │
│       │ c  │    │
╰───────┴────┴────╯
    """.strip()


def test_render_table_data_types():
    assert "\n".join(render_table([
        ["head1", "h2"],
        ROW_SEPARATOR,
        ["str", "A"],
        ["int", 42],
        ["none", None],
        ["true", True],
        ["false", False],
    ], alignments={0: 'right'})) == """
╭───────┬───────╮
│ head1 │ h2    │
├───────┼───────┤
│   str │ A     │
│   int │ 42    │
│  none │ None  │
│  true │ True  │
│ false │ False │
╰───────┴───────╯
    """.strip()


def test_flatten_rows_simple():
    flat_rows = list(_flatten_rows_with_lists(
        ['a', 'b', 'c'], False
    ))
    assert flat_rows == [
        ['a', 'b', 'c'],
    ]


def test_flatten_rows_with_list():
    flat_rows = list(_flatten_rows_with_lists(
        ['a', ['X', 'Y'], 'c'], False
    ))
    assert flat_rows == [
        ['a', 'X', 'c'],
        ['', 'Y', ''],
    ]


def test_flatten_rows_with_empty_list():
    flat_rows = list(_flatten_rows_with_lists(
        ['a', [], 'c'], False
    ))
    assert flat_rows == [
        ['a', '[]', 'c'],
    ]


def test_flatten_rows_with_set():
    flat_rows = list(_flatten_rows_with_lists(
        ['a', {'X', 'Y'}, 'c'], False
    ))
    assert flat_rows == [
        ['a', 'X', 'c'],
        ['', 'Y', ''],
    ]


def test_flatten_rows_with_tuple():
    flat_rows = list(_flatten_rows_with_lists(
        ['a', ('X', 'Y'), 'c'], False
    ))
    assert flat_rows == [
        ['a', 'X', 'c'],
        ['', 'Y', ''],
    ]


def test_flatten_rows_with_list_repeat():
    flat_rows = list(_flatten_rows_with_lists(
        [1, ['X', 'Y'], 'c'], True
    ))
    assert flat_rows == [
        ['1', 'X', 'c'],
        ['1', 'Y', 'c'],
    ]


def test_flatten_rows_with_two_list():
    flat_rows = list(_flatten_rows_with_lists(
        ['a', ['X', 'Y'], [1, 2, 3]], False
    ))
    assert flat_rows == [
        ['a', 'X', '1'],
        ['', 'Y', '2'],
        ['', '', '3'],
    ]


def test_flatten_rows_with_two_list_repeat():
    flat_rows = list(_flatten_rows_with_lists(
        ['a', ['X', 'Y'], [1, 2, 3]], True
    ))
    assert flat_rows == [
        ['a', 'X', '1'],
        ['a', 'Y', '2'],
        ['a', '', '3'],
    ]
