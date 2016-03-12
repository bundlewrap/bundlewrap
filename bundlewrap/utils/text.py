# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from io import BytesIO
from os import environ
from os.path import normpath
from random import choice
import re
from string import digits, ascii_letters

from . import Fault, STDERR_WRITER


ANSI_ESCAPE = re.compile(r'\x1b[^m]*m')
VALID_NAME_CHARS = digits + ascii_letters + "-_.+"


def ansi_wrapper(colorizer):
    if environ.get("BW_COLORS", "1") != "0":
        return colorizer
    else:
        return lambda s, **kwargs: s


@ansi_wrapper
def blue(text):
    return "\033[34m{}\033[0m".format(text)


@ansi_wrapper
def bold(text):
    return "\033[1m{}\033[0m".format(text)


@ansi_wrapper
def cyan(text):
    return "\033[36m{}\033[0m".format(text)


@ansi_wrapper
def inverse(text):
    return "\033[0m\033[7m{}\033[0m".format(text)


@ansi_wrapper
def green(text):
    return "\033[32m{}\033[0m".format(text)


@ansi_wrapper
def red(text):
    return "\033[31m{}\033[0m".format(text)


@ansi_wrapper
def yellow(text):
    return "\033[33m{}\033[0m".format(text)


def error_summary(errors):
    if not errors:
        return

    if len(errors) == 1:
        STDERR_WRITER.write(_("\n{x} There was an error, repeated below.\n\n").format(
            x=red("!!!"),
        ))
        STDERR_WRITER.flush()
    else:
        STDERR_WRITER.write(_("\n{x} There were {count} errors, repeated below.\n\n").format(
            count=len(errors),
            x=red("!!!"),
        ))
        STDERR_WRITER.flush()

    for e in errors:
        STDERR_WRITER.write(e)
        STDERR_WRITER.write("\n")
        STDERR_WRITER.flush()


def force_text(data):
    """
    Try to return a text aka unicode object from the given data.
    Also has Python 2/3 compatibility baked in. Oh the humanity.
    """
    if isinstance(data, bytes):
        return data.decode('utf-8', 'replace')
    elif isinstance(data, Fault):
        return data.value
    return data


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
    return ''.join(choice(ascii_letters + digits) for c in range(length))


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


def wrap_question(title, body, question, prefix=""):
    output = ("{0}\n"
              "{0} ╭─ {1}\n"
              "{0} │\n".format(prefix, title))
    for line in body.splitlines():
        output += "{0} │  {1}\n".format(prefix, line)
    output += ("{0} │\n"
               "{0} ╰─ ".format(prefix) + question)
    return output


class LineBuffer(object):
    def __init__(self, target):
        self.buffer = b""
        self.record = BytesIO()
        self.target = target if target else lambda s: None

    def close(self):
        self.flush()
        if self.buffer:
            self.record.write(self.buffer)
            self.target(self.buffer)

    def flush(self):
        while b"\n" in self.buffer:
            chunk, self.buffer = self.buffer.split(b"\n", 1)
            self.record.write(chunk + b"\n")
            self.target(chunk + b"\n")

    def write(self, msg):
        self.buffer += msg
        self.flush()
