from __future__ import unicode_literals

from .text import mark_for_translation as _


def ask_interactively(question, default, get_input=raw_input):
    answers = _("[Y/n]") if default else _("[y/N]")
    question = question + " " + answers + " "
    while True:
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
