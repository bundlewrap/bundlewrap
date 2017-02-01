# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from .text import ansi_clean


ROW_SEPARATOR = 1


def _column_widths_for_rows(rows):
    column_widths = [0 for column in rows[0]]
    for row in rows:
        if not isinstance(row, list) and not isinstance(row, tuple):
            continue
        for i, column in enumerate(row):
            column_widths[i] = max(column_widths[i], len(ansi_clean(column)))
    return column_widths


def _border_top(column_widths):
    result = "╭─"
    for column_width in column_widths:
        result += "─" * column_width
        result += "─┬─"
    return result[:-3] + "─╮"


def _border_center(column_widths):
    result = "├─"
    for column_width in column_widths:
        result += "─" * column_width
        result += "─┼─"
    return result[:-3] + "─┤"


def _border_bottom(column_widths):
    result = "╰─"
    for column_width in column_widths:
        result += "─" * column_width
        result += "─┴─"
    return result[:-3] + "─╯"


def _row(row, column_widths, alignments):
    result = "│ "
    for i, column_value in enumerate(row):
        alignment = alignments.get(i, 'left')
        if alignment == 'right':
            result += " " * (column_widths[i] - len(ansi_clean(column_value)))
            result += column_value
        elif alignment == 'left':
            result += column_value
            result += " " * (column_widths[i] - len(ansi_clean(column_value)))
        elif alignment == 'center':
            prefix = int((column_widths[i] - len(ansi_clean(column_value))) / 2)
            result += " " * prefix
            result += column_value
            result += " " * (column_widths[i] - len(ansi_clean(column_value)) - prefix)
        else:
            raise NotImplementedError("no such alignment: {}".format(alignment))
        result += " │ "
    return result[:-1]


def render_table(rows, alignments=None):
    """
    Yields lines for a table.

    rows must be a list of lists of values, with the first row being
    considered the heading row.

    alignments is a dict mapping column indexes to 'left' or 'right'.
    """
    if alignments is None:
        alignments = {}
    column_widths = _column_widths_for_rows(rows)

    yield _border_top(column_widths)

    for row_index, row in enumerate(rows):
        if row == ROW_SEPARATOR:
            yield _border_center(column_widths)
        elif row_index == 0:
            # heading row ignores alignments
            yield _row(row, column_widths, {})
        else:
            yield _row(row, column_widths, alignments)
    yield _border_bottom(column_widths)
