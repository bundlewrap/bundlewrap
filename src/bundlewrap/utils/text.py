# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from os import environ
from os.path import normpath
from random import choice
from string import digits, letters

from fabric import colors as _fabric_colors

VALID_NAME_CHARS = digits + letters + "-_.+"


def _ansi_wrapper(colorizer):
    if environ.get("BWCOLORS", "1") != "0":
        return colorizer
    else:
        return lambda s, **kwargs: s


def _bold_wrapper(text):
    return "\033[1m{}\033[0m".format(text)


bold = _ansi_wrapper(_bold_wrapper)
green = _ansi_wrapper(_fabric_colors.green)
red = _ansi_wrapper(_fabric_colors.red)
yellow = _ansi_wrapper(_fabric_colors.yellow)


def error_summary(errors):
    if not errors:
        return

    if len(errors) == 1:
        print(_("\n{x} There was an error, repeated below.\n").format(
            x=red("!!!"),
        ))
    else:
        print(_("\n{x} There were {count} errors, repeated below.\n").format(
            count=len(errors),
            x=red("!!!"),
        ))

    for e in errors:
        print(e)


def is_subdirectory(parent, child):
    """
    Returns True if the given child is a subdirectory of the parent.
    """
    parent = normpath(parent)
    child = normpath(child)

    if not parent.startswith("/") or not child.startswith("/"):
        raise ValueError(_("directory paths must be absolute"))

    if parent == child:
        return False

    if parent == "/":
        return True

    return child.startswith(parent + "/")


def mark_for_translation(s):
    return s
_ = mark_for_translation


def randstr(length=24):
    """
    Returns a random alphanumeric string of the given length.
    """
    return ''.join(choice(letters + digits) for c in range(length))


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


def wrap_question(title, body, question):
    output = ("\n"
              " ╭  {}\n"
              " ┃\n".format(title))
    for line in body.splitlines():
        output += " ┃   {}\n".format(line)
    output += (" ┃\n"
               " ╰  " + question)
    return output
