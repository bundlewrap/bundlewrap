# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from os import _exit, kill
from signal import SIGINT, signal
from sys import stderr

from .utils.text import blue, bold, mark_for_translation as _
from .utils.ui import QUIT_EVENT


SSH_PIDS = []


def sigint_handler(*args, **kwargs):
    if not QUIT_EVENT.is_set():
        stderr.write(_("\n{x} {signal}  stopping all tasks... (hit CTRL+C again for immediate dirty exit)\n").format(
            signal=bold(_("SIGINT")),
            x=blue("i"),
        ))
        QUIT_EVENT.set()
    else:
        stderr.write(_("\n{x} {signal}  canceling cleanup, exiting...\n").format(
            signal=bold(_("SIGINT")),
            x=blue("i"),
        ))
        for ssh_pid in SSH_PIDS:
            stderr.write(_("{x} {signal}  killing SSH session with PID {pid}\n").format(
                pid=ssh_pid,
                signal=bold(_("SIGINT")),
                x=blue("i"),
            ))
            try:
                kill(ssh_pid, SIGINT)
            except ProcessLookupError:
                pass
        _exit(1)

signal(SIGINT, sigint_handler)
