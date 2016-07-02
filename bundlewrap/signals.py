# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from os import _exit, kill
from signal import SIGINT, signal

from .utils.text import blue, bold, mark_for_translation as _
from .utils.ui import io, QUIT_EVENT


SSH_PIDS = []


def sigint_handler(*args, **kwargs):
    if not QUIT_EVENT.is_set():
        QUIT_EVENT.set()
        io.stderr(_(
            "{x} {signal}  canceling pending tasks... "
            "(hit CTRL+C again for immediate dirty exit)"
        ).format(
            signal=bold(_("SIGINT")),
            x=blue("i"),
        ))
    else:
        io.stderr(_("{x} {signal}  cleanup interrupted, exiting...").format(
            signal=bold(_("SIGINT")),
            x=blue("i"),
        ))
        for ssh_pid in SSH_PIDS:
            io.debug(_("killing SSH session with PID {pid}").format(pid=ssh_pid))
            try:
                kill(ssh_pid, SIGINT)
            except ProcessLookupError:
                pass
        io._clear_last_job()
        _exit(1)

signal(SIGINT, sigint_handler)
