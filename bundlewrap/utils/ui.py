from contextlib import contextmanager
from datetime import datetime
import fcntl
from functools import wraps
from multiprocessing import Lock, Manager
import os
from signal import signal, SIGPIPE, SIG_DFL
import struct
import sys
import termios

from . import STDERR_WRITER, STDOUT_WRITER
from .text import ANSI_ESCAPE, inverse, mark_for_translation as _

TTY = STDOUT_WRITER.isatty()


try:
    input_function = raw_input
except NameError:  # Python 3
    input_function = input

# prevent BrokenPipeError when piping into `head`
# http://stackoverflow.com/questions/14207708/ioerror-errno-32-broken-pipe-python
signal(SIGPIPE, SIG_DFL)


def add_debug_timestamp(f):
    @wraps(f)
    def wrapped(self, msg):
        if self.debug_mode:
            msg = datetime.now().strftime("[%Y-%m-%d %H:%M:%S.%f] ") + msg
        return f(self, msg)
    return wrapped


def clear_formatting(f):
    """
    Makes sure formatting from cut-off lines can't bleed into next one
    """
    @wraps(f)
    def wrapped(self, msg):
        if TTY and os.environ.get("BWCOLORS", "1") != "0":
            msg = "\033[0m" + msg
        return f(self, msg)
    return wrapped


def term_width():
    if not TTY:
        return 0

    fd = sys.stdout.fileno()
    _, width = struct.unpack('hh', fcntl.ioctl(fd, termios.TIOCGWINSZ, 'aaaa'))
    return width


def write_to_stream(stream, msg):
    if TTY:
        stream.write(msg)
    else:
        stream.write(ANSI_ESCAPE.sub("", msg))
    stream.flush()


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
            if self.jobs and TTY:
                write_to_stream(STDOUT_WRITER, "\r\033[K")
            while True:
                STDOUT_WRITER.write("\a")
                STDOUT_WRITER.write(question)
                STDOUT_WRITER.flush()

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
                STDOUT_WRITER.write(_("Please answer with 'y(es)' or 'n(o)'.\n"))
                STDOUT_WRITER.flush()
            if epilogue:
                STDOUT_WRITER.write(epilogue + "\n")
                STDOUT_WRITER.flush()
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
    def debug(self, msg):
        if self.debug_mode:
            with self.lock:
                self._write(msg)

    def job_add(self, msg):
        with self.lock:
            if TTY:
                if self.jobs:
                    write_to_stream(STDOUT_WRITER, "\r\033[K")
                write_to_stream(STDOUT_WRITER, inverse("{} ".format(msg)[:term_width() - 1]))
            self.jobs.append(msg)

    def job_del(self, msg):
        with self.lock:
            self.jobs.remove(msg)
            if TTY:
                write_to_stream(STDOUT_WRITER, "\r\033[K")
            self._write_current_job()

    @clear_formatting
    @add_debug_timestamp
    def stderr(self, msg):
        with self.lock:
            self._write(msg, err=True)

    @clear_formatting
    @add_debug_timestamp
    def stdout(self, msg):
        with self.lock:
            self._write(msg)

    @contextmanager
    def job(self, job_text):
        self.job_add(job_text)
        try:
            yield
        finally:
            self.job_del(job_text)

    def _write(self, msg, err=False):
        if self.jobs and TTY:
            write_to_stream(STDOUT_WRITER, "\r\033[K")
        if msg is not None:
            write_to_stream(STDERR_WRITER if err else STDOUT_WRITER, msg + "\n")
        self._write_current_job()

    def _write_current_job(self):
        if self.jobs and TTY:
            write_to_stream(STDOUT_WRITER, inverse("{} ".format(self.jobs[-1])[:term_width() - 1]))

io = IOManager()
