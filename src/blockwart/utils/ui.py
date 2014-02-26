from __future__ import unicode_literals

from sys import stdout

from .text import mark_for_translation as _


class LineBuffer(object):
    def __init__(self, target):
        self.buffer = b""
        self.target = target

    def flush(self):
        self.buffer = self.buffer.replace(b"\r", b"\n")
        while b"\n" in self.buffer:
            chunk, self.buffer = self.buffer.split(b"\n", 1)
            self.target(chunk)

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
