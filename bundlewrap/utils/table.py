from os import environ

from .text import ansi_clean


ROW_SEPARATOR = 1

if environ.get("BW_TABLE_STYLE") == 'ascii':
    FRAME_TOP_LEFT = "+-"
    FRAME_TOP_COLUMN_SEPARATOR = "-+-"
    FRAME_TOP_RIGHT = "-+"
    FRAME_BOTTOM_LEFT = "+-"
    FRAME_BOTTOM_COLUMN_SEPARATOR = "-+-"
    FRAME_BOTTOM_RIGHT = "-+"
    FRAME_CENTER_LEFT = "+-"
    FRAME_CENTER_COLUMN_SEPARATOR = "-+-"
    FRAME_CENTER_RIGHT = "-+"
    FRAME_COLUMN_FILLER = "-"
    FRAME_COLUMN_WHITESPACE = " "
    FRAME_ROW_COLUMN_SEPARATOR_LEFT = "-| "
    FRAME_ROW_COLUMN_SEPARATOR_NONE = " | "
    FRAME_ROW_COLUMN_SEPARATOR_BOTH = "-+-"
    FRAME_ROW_COLUMN_SEPARATOR_RIGHT = " |-"
elif environ.get("BW_TABLE_STYLE") == 'grep':
    FRAME_TOP_LEFT = ""
    FRAME_TOP_COLUMN_SEPARATOR = ""
    FRAME_TOP_RIGHT = ""
    FRAME_BOTTOM_LEFT = ""
    FRAME_BOTTOM_COLUMN_SEPARATOR = ""
    FRAME_BOTTOM_RIGHT = ""
    FRAME_CENTER_LEFT = ""
    FRAME_CENTER_COLUMN_SEPARATOR = ""
    FRAME_CENTER_RIGHT = ""
    FRAME_COLUMN_FILLER = ""
    FRAME_COLUMN_WHITESPACE = ""
    FRAME_ROW_COLUMN_SEPARATOR_LEFT = "\t"
    FRAME_ROW_COLUMN_SEPARATOR_NONE = "\t"
    FRAME_ROW_COLUMN_SEPARATOR_BOTH = "\t"
    FRAME_ROW_COLUMN_SEPARATOR_RIGHT = "\t"
else:
    FRAME_TOP_LEFT = "╭─"
    FRAME_TOP_COLUMN_SEPARATOR = "─┬─"
    FRAME_TOP_RIGHT = "─╮"
    FRAME_BOTTOM_LEFT = "╰─"
    FRAME_BOTTOM_COLUMN_SEPARATOR = "─┴─"
    FRAME_BOTTOM_RIGHT = "─╯"
    FRAME_CENTER_LEFT = "├─"
    FRAME_CENTER_COLUMN_SEPARATOR = "─┼─"
    FRAME_CENTER_RIGHT = "─┤"
    FRAME_COLUMN_FILLER = "─"
    FRAME_COLUMN_WHITESPACE = " "
    FRAME_ROW_COLUMN_SEPARATOR_LEFT = "─┤ "
    FRAME_ROW_COLUMN_SEPARATOR_NONE = " │ "
    FRAME_ROW_COLUMN_SEPARATOR_BOTH = "─┼─"
    FRAME_ROW_COLUMN_SEPARATOR_RIGHT = " ├─"


def _column_widths_for_rows(rows):
    column_widths = [0 for column in rows[0]]
    for row in rows:
        if not isinstance(row, list) and not isinstance(row, tuple):
            continue
        for i, column in enumerate(row):
            if column == ROW_SEPARATOR:
                continue
            column_widths[i] = max(column_widths[i], len(ansi_clean(column)))
    return column_widths


def _border_top(column_widths):
    result = FRAME_TOP_LEFT
    result += FRAME_TOP_COLUMN_SEPARATOR.join(
        [FRAME_COLUMN_FILLER * width for width in column_widths]
    )
    result += FRAME_TOP_RIGHT
    return result


def _border_center(column_widths):  # FIXME unused?
    result = FRAME_CENTER_LEFT
    result += FRAME_CENTER_COLUMN_SEPARATOR.join(
        [FRAME_COLUMN_FILLER * width for width in column_widths]
    )
    result += FRAME_CENTER_RIGHT
    return result


def _border_bottom(column_widths):
    result = FRAME_BOTTOM_LEFT
    result += FRAME_BOTTOM_COLUMN_SEPARATOR.join(
        [FRAME_COLUMN_FILLER * width for width in column_widths]
    )
    result += FRAME_BOTTOM_RIGHT
    return result


def _empty_row(row):
    for column_value in row:
        if column_value != ROW_SEPARATOR and column_value.strip():
            return False
    return True


def _row(row, column_widths, alignments):
    result = ""
    columns = []
    for i, column_value in enumerate(row):
        alignment = alignments.get(i, 'left')
        if column_value == ROW_SEPARATOR:
            columns.append(ROW_SEPARATOR)
        elif alignment == 'right':
            columns.append(
                FRAME_COLUMN_WHITESPACE * (column_widths[i] - len(ansi_clean(column_value))) +
                column_value
            )
        elif alignment == 'left':
            columns.append(
                column_value +
                FRAME_COLUMN_WHITESPACE * (column_widths[i] - len(ansi_clean(column_value)))
            )
        elif alignment == 'center':
            prefix = int((column_widths[i] - len(ansi_clean(column_value))) / 2)
            suffix = (column_widths[i] - len(ansi_clean(column_value)) - prefix)
            columns.append(
                FRAME_COLUMN_WHITESPACE * prefix +
                column_value +
                FRAME_COLUMN_WHITESPACE * suffix
            )
        else:
            raise NotImplementedError("no such alignment: {}".format(alignment))

    for i, column_value in enumerate(columns):
        if i == 0:
            fill_previous_column = False
        else:
            fill_previous_column = columns[i - 1] == ROW_SEPARATOR
        fill_this_column = column_value == ROW_SEPARATOR

        if fill_previous_column and fill_this_column:
            result += FRAME_ROW_COLUMN_SEPARATOR_BOTH
        elif fill_previous_column and not fill_this_column:
            result += FRAME_ROW_COLUMN_SEPARATOR_LEFT
        elif not fill_previous_column and fill_this_column:
            result += FRAME_ROW_COLUMN_SEPARATOR_RIGHT
        else:
            result += FRAME_ROW_COLUMN_SEPARATOR_NONE

        if fill_this_column:
            result += FRAME_COLUMN_FILLER * column_widths[i]
        else:
            result += column_value

    if fill_this_column:
        result += FRAME_ROW_COLUMN_SEPARATOR_LEFT
    else:
        result += FRAME_ROW_COLUMN_SEPARATOR_NONE

    return result[1:-1]  # strip exactly one whitespace character at each end


def render_table(rows, alignments=None):
    """
    Yields lines for a table.

    rows must be a list of lists of values, with the first row being
    considered the heading row. Alternatively, an entire row or
    individual cells can be set to ROW_SEPARATOR to turn it into a
    separator:

    rows = [
        ["heading1", "heading2"],
        ROW_SEPARATOR,
        ["value1", "value2"],
        ["value3", ROW_SEPARATOR],
    ]

    alignments is a dict mapping column indexes to 'left' or 'right'.
    """
    if alignments is None:
        alignments = {}
    column_widths = _column_widths_for_rows(rows)

    if environ.get("BW_TABLE_STYLE") != 'grep':
        yield _border_top(column_widths)

    for row_index, row in enumerate(rows):
        if row == ROW_SEPARATOR:
            if environ.get("BW_TABLE_STYLE") != 'grep':
                yield _row([ROW_SEPARATOR] * len(column_widths), column_widths, {})
        elif row_index == 0:
            # heading row ignores alignments
            yield _row(row, column_widths, {})
        elif environ.get("BW_TABLE_STYLE") != 'grep' or not _empty_row(row):
            yield _row(row, column_widths, alignments)

    if environ.get("BW_TABLE_STYLE") != 'grep':
        yield _border_bottom(column_widths)
