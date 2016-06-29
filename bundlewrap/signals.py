# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from os import _exit, kill
from signal import SIGINT, signal
from sys import stderr

from .utils.text import blue, bold, force_text, LineBuffer, mark_for_translation as _, randstr
from .utils.ui import io, QUIT_EVENT


SSH_PIDS = []


def sigint_handler(*args, **kwargs):
    if not QUIT_EVENT.is_set():
        stderr.write("\n{x} {signal}  {shutdown}\n".format(
            shutdown=_("Asking for a soft shutdown, please stand by ..."),
            signal=bold(_("SIGINT")),
            x=blue("i"),
        ))
        QUIT_EVENT.set()
    else:
        stderr.write("\n{x} {signal}  {shutdown}\n".format(
            shutdown=_("Doing a hard shutdown"),
            signal=bold(_("SIGINT")),
            x=blue("i"),
        ))
        for ssh_pid in SSH_PIDS:
            stderr.write("{x} {signal}  {sending} {pid}\n".format(
                pid=ssh_pid,
                sending=_("Sending SIGINT to SSH PID"),
                signal=bold(_("SIGINT")),
                x=blue("i"),
            ))
            try:
                kill(ssh_pid, SIGINT)
            except ProcessLookupError:
                pass
        _exit(1)

signal(SIGINT, sigint_handler)
