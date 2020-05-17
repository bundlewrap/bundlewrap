from bundlewrap.utils.table import ROW_SEPARATOR, render_table


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
