from contextlib import contextmanager
from datetime import datetime
from errno import EPIPE
import fcntl
from functools import wraps
from os import _exit, environ, kill
from select import select
from signal import signal, SIG_DFL, SIGINT, SIGTERM
import struct
import sys
import termios
from threading import Event, Lock, Thread

from . import STDERR_WRITER, STDOUT_WRITER
from .text import ANSI_ESCAPE, blue, bold, inverse, mark_for_translation as _

QUIT_EVENT = Event()
SHUTDOWN_EVENT_HARD = Event()
SHUTDOWN_EVENT_SOFT = Event()
TTY = STDOUT_WRITER.isatty()


if sys.version_info >= (3, 0):
    broken_pipe_exception = BrokenPipeError
else:
    broken_pipe_exception = IOError


def add_debug_indicator(f):
    @wraps(f)
    def wrapped(self, msg, **kwargs):
        return f(self, "[DEBUG] " + msg, **kwargs)
    return wrapped


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
        if TTY and environ.get("BW_COLORS", "1") != "0":
            msg = "\033[0m" + msg
        return f(self, msg, **kwargs)
    return wrapped


def sigint_handler(*args, **kwargs):
    """
    This handler is kept short since it interrupts execution of the
    main thread. It's safer to handle these events in their own thread
    because the main thread might be holding the IO lock while it is
    interrupted.
    """
    if not SHUTDOWN_EVENT_SOFT.is_set():
        SHUTDOWN_EVENT_SOFT.set()
    else:
        SHUTDOWN_EVENT_HARD.set()


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
        while True:
            if QUIT_EVENT.is_set():
                return None
            if select([sys.stdin], [], [], 0.1)[0]:
                return sys.stdin.readline().strip()

    def drain(self):
        if sys.stdin.isatty():
            termios.tcflush(sys.stdin, termios.TCIFLUSH)


class IOManager(object):
    """
    Threadsafe singleton class that handles all IO.
    """
    def __init__(self):
        self._active = False
        self.debug_mode = False
        self.jobs = []
        self.lock = Lock()
        self._signal_handler_thread = Thread(
            target=self._signal_handler_thread_body,
        )
        # daemon mode is required because we need to keep the thread
        # around until the end of a soft shutdown to wait for a hard
        # shutdown signal, but don't have a feasible way of stopping
        # the thread once the soft shutdown has completed
        self._signal_handler_thread.daemon = True
        self._ssh_pids = []

    def activate(self):
        self._active = True
        self._signal_handler_thread.start()
        signal(SIGINT, sigint_handler)

    def ask(self, question, default, epilogue=None, input_handler=DrainableStdin()):
        assert self._active
        answers = _("[Y/n]") if default else _("[y/N]")
        question = question + " " + answers + " "
        with self.lock:
            if QUIT_EVENT.is_set():
                sys.exit(0)
            self._clear_last_job()
            while True:
                write_to_stream(STDOUT_WRITER, "\a" + question)

                input_handler.drain()
                answer = input_handler.get_input()
                if answer is None:
                    if epilogue:
                        write_to_stream(STDOUT_WRITER, "\n" + epilogue + "\n")
                    QUIT_EVENT.set()
                    sys.exit(0)
                elif answer.lower() in (_("y"), _("yes")) or (
                    not answer and default
                ):
                    answer = True
                    break
                elif answer.lower() in (_("n"), _("no")) or (
                    not answer and not default
                ):
                    answer = False
                    break
                write_to_stream(
                    STDOUT_WRITER,
                    _("Please answer with 'y(es)' or 'n(o)'.\n"),
                )
            if epilogue:
                write_to_stream(STDOUT_WRITER, epilogue + "\n")
            self._write_current_job()
        return answer

    def deactivate(self):
        self._active = False
        signal(SIGINT, SIG_DFL)
        self._signal_handler_thread.join()

    @clear_formatting
    @add_debug_indicator
    @add_debug_timestamp
    def debug(self, msg, append_newline=True):
        if self.debug_mode:
            with self.lock:
                self._write(msg, append_newline=append_newline)

    def job_add(self, msg):
        if not self._active:
            return
        with self.lock:
            if TTY:
                self._clear_last_job()
                write_to_stream(STDOUT_WRITER, inverse("{} ".format(msg)[:term_width() - 1]))
            self.jobs.append(msg)

    def job_del(self, msg):
        if not self._active:
            return
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

    def _signal_handler_thread_body(self):
        while self._active:
            if QUIT_EVENT.is_set():
                if SHUTDOWN_EVENT_HARD.wait(0.1):
                    self.stderr(_("{x} {signal}  cleanup interrupted, exiting...").format(
                        signal=bold(_("SIGINT")),
                        x=blue("i"),
                    ))
                    for ssh_pid in self._ssh_pids:
                        self.debug(_("killing SSH session with PID {pid}").format(pid=ssh_pid))
                        try:
                            kill(ssh_pid, SIGTERM)
                        except ProcessLookupError:
                            pass
                    self._clear_last_job()
                    _exit(1)
            else:
                if SHUTDOWN_EVENT_SOFT.wait(0.1):
                    QUIT_EVENT.set()
                    self.stderr(_(
                        "{x} {signal}  canceling pending tasks... "
                        "(hit CTRL+C again for immediate dirty exit)"
                    ).format(
                        signal=bold(_("SIGINT")),
                        x=blue("i"),
                    ))

    def _write(self, msg, append_newline=True, err=False):
        if not self._active:
            return
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
