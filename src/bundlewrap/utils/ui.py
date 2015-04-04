# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from io import BytesIO
from sys import stdout

from .text import mark_for_translation as _


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


def ask_interactively(question, default, get_input=raw_input):
    answers = _("[Y/n]") if default else _("[y/N]")
    question = question + " " + answers + " "
    while True:
        stdout.write("\a")
        stdout.flush()

        answer = get_input(question.encode('utf-8'))
        if answer.lower() in (_("y"), _("yes")) or (
            not answer and default
        ):
            return True
        elif answer.lower() in (_("n"), _("no")) or (
            not answer and not default
        ):
            return False
        print(_("Please answer with 'y(es)' or 'n(o)'."))
