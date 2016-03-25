from contextlib import contextmanager
from datetime import datetime
from errno import EPIPE
import fcntl
from functools import wraps
import os
import struct
import sys
import termios
from threading import Lock

from . import STDERR_WRITER, STDOUT_WRITER
from .text import ANSI_ESCAPE, inverse, mark_for_translation as _

TTY = STDOUT_WRITER.isatty()


if sys.version_info >= (3, 0):
    broken_pipe_exception = BrokenPipeError
else:
    broken_pipe_exception = IOError


def add_debug_timestamp(f):
    @wraps(f)
    def wrapped(self, msg, **kwargs):
        if self.debug_mode:
            msg = datetime.now().strftime("[%Y-%m-%d %H:%M:%S.%f] ") + msg
        return f(self, msg, **kwargs)
    return wrapped


def clear_formatting(f):
    """
    Makes sure formatting from cut-off lines can't bleed into next one
    """
    @wraps(f)
    def wrapped(self, msg, **kwargs):
        if TTY and os.environ.get("BW_COLORS", "1") != "0":
            msg = "\033[0m" + msg
        return f(self, msg, **kwargs)
    return wrapped


def term_width():
    if not TTY:
        return 0

    fd = sys.stdout.fileno()
    _, width = struct.unpack('hh', fcntl.ioctl(fd, termios.TIOCGWINSZ, 'aaaa'))
    return width


def write_to_stream(stream, msg):
    try:
        if TTY:
            stream.write(msg)
        else:
            stream.write(ANSI_ESCAPE.sub("", msg))
        stream.flush()
    except broken_pipe_exception as e:
        if broken_pipe_exception == IOError:
            if e.errno != EPIPE:
                raise


class DrainableStdin(object):
    def get_input(self):
        try:
            return raw_input()
        except NameError:  # Python 3
            return input()

    def drain(self):
        termios.tcflush(sys.stdin, termios.TCIFLUSH)


class IOManager(object):
    def __init__(self):
        self.debug_mode = False
        self.jobs = []
        self.lock = Lock()

    def ask(self, question, default, epilogue=None, input_handler=DrainableStdin()):
        answers = _("[Y/n]") if default else _("[y/N]")
        question = question + " " + answers + " "
        with self.lock:
            self._clear_last_job()
            while True:
                write_to_stream(STDOUT_WRITER, "\a" + question)

                input_handler.drain()
                answer = input_handler.get_input()
                if answer.lower() in (_("y"), _("yes")) or (
                    not answer and default
                ):
                    answer = True
                    break
                elif answer.lower() in (_("n"), _("no")) or (
                    not answer and not default
                ):
                    answer = False
                    break
                write_to_stream(STDOUT_WRITER, _("Please answer with 'y(es)' or 'n(o)'.\n"))
            if epilogue:
                write_to_stream(STDOUT_WRITER, epilogue + "\n")
            self._write_current_job()
        return answer

    @clear_formatting
    @add_debug_timestamp
    def debug(self, msg, append_newline=True):
        if self.debug_mode:
            with self.lock:
                self._write(msg, append_newline=append_newline)

    def job_add(self, msg):
        with self.lock:
            if TTY:
                self._clear_last_job()
                write_to_stream(STDOUT_WRITER, inverse("{} ".format(msg)[:term_width() - 1]))
            self.jobs.append(msg)

    def job_del(self, msg):
        with self.lock:
            self._clear_last_job()
            self.jobs.remove(msg)
            self._write_current_job()

    @clear_formatting
    @add_debug_timestamp
    def stderr(self, msg, append_newline=True):
        with self.lock:
            self._write(msg, append_newline=append_newline, err=True)

    @clear_formatting
    @add_debug_timestamp
    def stdout(self, msg, append_newline=True):
        with self.lock:
            self._write(msg, append_newline=append_newline)

    @contextmanager
    def job(self, job_text):
        self.job_add(job_text)
        try:
            yield
        finally:
            self.job_del(job_text)

    def _clear_last_job(self):
        if self.jobs and TTY:
            write_to_stream(STDOUT_WRITER, "\r\033[K")

    def _write(self, msg, append_newline=True, err=False):
        if self.jobs and TTY:
            write_to_stream(STDOUT_WRITER, "\r\033[K")
        if msg is not None:
            if append_newline:
                msg += "\n"
            write_to_stream(STDERR_WRITER if err else STDOUT_WRITER, msg)
        self._write_current_job()

    def _write_current_job(self):
        if self.jobs and TTY:
            write_to_stream(STDOUT_WRITER, inverse("{} ".format(self.jobs[-1])[:term_width() - 1]))

io = IOManager()
