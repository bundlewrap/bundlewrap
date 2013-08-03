from string import digits, letters
from sys import stdout

from fabric import colors as _fabric_colors

VALID_NAME_CHARS = digits + letters + "-_.+"


def _color_wrapper(colorizer):
    if stdout.isatty():
        return colorizer
    else:
        return lambda s, **kwargs: s

green = _color_wrapper(_fabric_colors.green)
red = _color_wrapper(_fabric_colors.red)
white = _color_wrapper(_fabric_colors.white)
yellow = _color_wrapper(_fabric_colors.yellow)


def mark_for_translation(s):
    return s


def validate_name(name):
    """
    Checks whether the given string is a valid name for a node, group,
    or bundle.
    """
    try:
        for char in name:
            assert char in VALID_NAME_CHARS
        assert not name.startswith(".")
    except AssertionError:
        return False
    return True
