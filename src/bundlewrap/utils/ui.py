# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from codecs import getwriter
from io import BytesIO
from sys import stdout

from .text import mark_for_translation as _


try:
    input_function = raw_input
except NameError:  # Python 3
    input_function = input

try:
    STDOUT_WRITER = getwriter('utf-8')(stdout.buffer)
except AttributeError:  # Python 2
    STDOUT_WRITER = getwriter('utf-8')(stdout)


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


def ask_interactively(question, default, get_input=input_function):
    answers = _("[Y/n]") if default else _("[y/N]")
    question = question + " " + answers + " "
    while True:
        STDOUT_WRITER.write("\a")
        STDOUT_WRITER.write(question)
        STDOUT_WRITER.flush()

        answer = get_input()
        if answer.lower() in (_("y"), _("yes")) or (
            not answer and default
        ):
            return True
        elif answer.lower() in (_("n"), _("no")) or (
            not answer and not default
        ):
            return False
        STDOUT_WRITER.write(_("Please answer with 'y(es)' or 'n(o)'.\n"))
        STDOUT_WRITER.flush()
