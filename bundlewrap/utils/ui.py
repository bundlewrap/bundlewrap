from contextlib import contextmanager
from datetime import datetime
from errno import EPIPE
import fcntl
from functools import wraps
from multiprocessing import Lock, Manager
import os
import struct
import sys
import termios

from . import STDERR_WRITER, STDOUT_WRITER
from .text import ANSI_ESCAPE, inverse, mark_for_translation as _

TTY = STDOUT_WRITER.isatty()


try:
    input_function = raw_input
    broken_pipe_exception = IOError
except NameError:  # Python 3
    broken_pipe_exception = BrokenPipeError
    input_function = input


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
        if TTY and os.environ.get("BWCOLORS", "1") != "0":
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


class IOManager(object):
    def __init__(self):
        self.capture_mode = False
        self.child_mode = False
        self.parent_mode = False

    def activate_as_child(self, lock, jobs, debug_mode, stdin):
        self.parent_mode = False
        self.child_mode = True
        self.debug_mode = debug_mode
        self.lock = lock
        self.jobs = jobs
        sys.stdin = stdin

    def activate_as_parent(self, debug=False):
        assert not self.child_mode
        self.debug_mode = debug
        self.jobs = Manager().list()
        self.lock = Lock()
        self.parent_mode = True

    def ask(self, question, default, epilogue=None, get_input=input_function):
        answers = _("[Y/n]") if default else _("[y/N]")
        question = question + " " + answers + " "
        with self.lock:
            self._clear_last_job()
            while True:
                write_to_stream(STDOUT_WRITER, "\a" + question)

                answer = get_input()
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

    @property
    def child_parameters(self):
        try:
            new_stdin = os.fdopen(os.dup(sys.stdin.fileno()))
        except ValueError:  # with pytest: redirected Stdin is pseudofile, has no fileno()
            new_stdin = sys.stdin
        return (
            self.lock,
            self.jobs,
            self.debug_mode,
            new_stdin,
        )

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
