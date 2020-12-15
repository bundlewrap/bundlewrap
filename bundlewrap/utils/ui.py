from contextlib import contextmanager, suppress
from datetime import datetime
from functools import wraps
from os import _exit, environ, getpid, kill
from os.path import join
from select import select
from shutil import get_terminal_size
from signal import signal, SIG_DFL, SIGINT, SIGQUIT, SIGTERM
from subprocess import PIPE, Popen
import sys
import termios
from time import time
from threading import Event, Lock, Thread

from . import STDERR_WRITER, STDOUT_WRITER
from .table import render_table, ROW_SEPARATOR
from .text import (
    HIDE_CURSOR,
    SHOW_CURSOR,
    ansi_clean,
    blue,
    bold,
    format_duration,
    mark_for_translation as _,
)


INFO_EVENT = Event()
QUIT_EVENT = Event()
SHUTDOWN_EVENT_HARD = Event()
SHUTDOWN_EVENT_SOFT = Event()
TTY = STDOUT_WRITER.isatty()


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


def capture_for_debug_logfile(f):
    @wraps(f)
    def wrapped(self, msg, **kwargs):
        if self.debug_log_file and self._active:
            self.debug_log_file.write(
                datetime.now().strftime("[%Y-%m-%d %H:%M:%S.%f] ") +
                ansi_clean(msg).rstrip("\n") + "\n"
            )
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


def sigquit_handler(*args, **kwargs):
    """
    This handler is kept short since it interrupts execution of the
    main thread. It's safer to handle these events in their own thread
    because the main thread might be holding the IO lock while it is
    interrupted.
    """
    INFO_EVENT.set()


def spinner():
    while True:
        for c in "⠁⠈⠐⠠⢀⡀⠄⠂":
            yield c


def page_lines(lines):
    """
    View the given list of Unicode lines in a pager (e.g. `less`).
    """
    lines = list(lines)
    line_width = max([len(ansi_clean(line)) for line in lines])
    if (
        TTY and (
            line_width > get_terminal_size().columns or
            len(lines) > get_terminal_size().lines
        )
    ):
        write_to_stream(STDOUT_WRITER, SHOW_CURSOR)
        env = environ.copy()
        env["LESS"] = env.get("LESS", "") + " -R"
        pager = Popen(
            [environ.get("PAGER", "/usr/bin/less")],
            env=env,
            stdin=PIPE,
        )
        with suppress(BrokenPipeError):
            pager.stdin.write("\n".join(lines).encode('utf-8'))
        pager.stdin.close()
        pager.communicate()
        write_to_stream(STDOUT_WRITER, HIDE_CURSOR)
    else:
        for line in lines:
            io.stdout(line)


def write_to_stream(stream, msg):
    with suppress(BrokenPipeError):
        if TTY:
            stream.write(msg)
        else:
            stream.write(ansi_clean(msg))
        stream.flush()


class DrainableStdin:
    def get_input(self):
        while True:
            if QUIT_EVENT.is_set():
                return None
            if select([sys.stdin], [], [], 0.1)[0]:
                return sys.stdin.readline().strip()

    def drain(self):
        if sys.stdin.isatty():
            termios.tcflush(sys.stdin, termios.TCIFLUSH)


class IOManager:
    """
    Threadsafe singleton class that handles all IO.
    """
    def __init__(self):
        self._active = False
        self.debug_log_file = None
        self.debug_mode = False
        self.jobs = []
        self.lock = Lock()
        self.progress = 0
        self.progress_start = None
        self.progress_total = 0
        self._spinner = spinner()
        self._last_spinner_character = next(self._spinner)
        self._last_spinner_update = 0
        self._signal_handler_thread = None
        self._child_pids = []
        self._status_line_present = False
        self._waiting_for_input = False

    def activate(self):
        self._active = True
        if 'BW_DEBUG_LOG_DIR' in environ:
            self.debug_log_file = open(join(
                environ['BW_DEBUG_LOG_DIR'],
                "{}_{}.log".format(
                    datetime.now().strftime("%Y-%m-%d_%H-%M-%S"),
                    getpid(),
                ),
            ), 'a')
        self._signal_handler_thread = Thread(
            target=self._signal_handler_thread_body,
        )
        # daemon mode is required because we need to keep the thread
        # around until the end of a soft shutdown to wait for a hard
        # shutdown signal, but don't have a feasible way of stopping
        # the thread once the soft shutdown has completed
        self._signal_handler_thread.daemon = True
        self._signal_handler_thread.start()
        signal(SIGINT, sigint_handler)
        signal(SIGQUIT, sigquit_handler)
        if TTY:
            write_to_stream(STDOUT_WRITER, HIDE_CURSOR)

    def ask(self, question, default, epilogue=None, input_handler=DrainableStdin()):
        assert self._active
        answers = _("[Y/n]") if default else _("[y/N]")
        question = question + " " + answers + " "
        self._waiting_for_input = True
        with self.lock:
            if QUIT_EVENT.is_set():
                sys.exit(0)
            self._clear_last_job()
            while True:
                write_to_stream(STDOUT_WRITER, "\a" + question + SHOW_CURSOR)

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
            write_to_stream(STDOUT_WRITER, HIDE_CURSOR)
        self._waiting_for_input = False
        return answer

    def deactivate(self):
        self._active = False
        if TTY:
            write_to_stream(STDOUT_WRITER, SHOW_CURSOR)
        signal(SIGINT, SIG_DFL)
        signal(SIGQUIT, SIG_DFL)
        self._signal_handler_thread.join()
        if self.debug_log_file:
            self.debug_log_file.close()

    @clear_formatting
    @add_debug_indicator
    @capture_for_debug_logfile
    @add_debug_timestamp
    def debug(self, msg, append_newline=True):
        if self.debug_mode:
            with self.lock:
                self._write(msg, append_newline=append_newline)

    def job_add(self, msg):
        if not self._active:
            return
        with self.lock:
            self._clear_last_job()
            self.jobs.append(msg)
            self._write_current_job()

    def job_del(self, msg):
        if not self._active:
            return
        with self.lock:
            self._clear_last_job()
            self.jobs.remove(msg)
            self._write_current_job()

    def progress_advance(self, increment=1):
        with self.lock:
            self.progress += increment

    def progress_increase_total(self, increment=1):
        with self.lock:
            self.progress_total += increment

    def progress_set_total(self, total):
        self.progress = 0
        self.progress_start = datetime.utcnow()
        self.progress_total = total

    def progress_show(self):
        if INFO_EVENT.is_set():
            INFO_EVENT.clear()
            table = []
            if self.jobs:
                table.append([bold(_("Running jobs")), self.jobs[0].strip()])
                for job in self.jobs[1:]:
                    table.append(["", job.strip()])
            try:
                progress = (self.progress / float(self.progress_total))
                elapsed = datetime.utcnow() - self.progress_start
                remaining = elapsed / progress - elapsed
            except ZeroDivisionError:
                pass
            else:
                if table:
                    table.append(ROW_SEPARATOR)
                table.extend([
                    [bold(_("Progress")), "{:.1f}%".format(progress * 100)],
                    ROW_SEPARATOR,
                    [bold(_("Elapsed")), format_duration(elapsed)],
                    ROW_SEPARATOR,
                    [
                        bold(_("Remaining")),
                        _("{} (estimate based on progress)").format(format_duration(remaining))
                    ],
                ])
            output = blue("i") + "\n"
            if table:
                for line in render_table(table):
                    output += ("{x} {line}\n".format(x=blue("i"), line=line))
            else:
                output += _("{x}  No progress info available at this time.\n").format(x=blue("i"))
            io.stderr(output + blue("i"))

    @clear_formatting
    @capture_for_debug_logfile
    @add_debug_timestamp
    def stderr(self, msg, append_newline=True):
        with self.lock:
            self._write(msg, append_newline=append_newline, err=True)

    @clear_formatting
    @capture_for_debug_logfile
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

    def job_wrapper(self, job_text):
        def outer_wrapper(wrapped_function):
            @wraps(wrapped_function)
            def inner_wrapper(*args, **kwargs):
                with self.job(job_text.format(*args, **kwargs)):
                    return wrapped_function(*args, **kwargs)
            return inner_wrapper
        return outer_wrapper

    def _clear_last_job(self):
        if self._status_line_present and TTY:
            write_to_stream(STDOUT_WRITER, "\r\033[K")
            self._status_line_present = False

    def _signal_handler_thread_body(self):
        while self._active:
            self.progress_show()
            if not self._waiting_for_input:  # do not block and ignore SIGINT while .ask()ing
                with self.lock:
                    self._clear_last_job()
                    self._write_current_job()
            if QUIT_EVENT.is_set():
                if SHUTDOWN_EVENT_HARD.wait(0.1):
                    self.stderr(_("{x} {signal}  cleanup interrupted, exiting...").format(
                        signal=bold(_("SIGINT")),
                        x=blue("i"),
                    ))
                    for ssh_pid in self._child_pids:
                        self.debug(_("killing SSH session with PID {pid}").format(pid=ssh_pid))
                        with suppress(ProcessLookupError):
                            kill(ssh_pid, SIGTERM)
                    self._clear_last_job()
                    if TTY:
                        write_to_stream(STDOUT_WRITER, SHOW_CURSOR)
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

    def _spinner_character(self):
        if time() - self._last_spinner_update > 0.2:
            self._last_spinner_update = time()
            self._last_spinner_character = next(self._spinner)
        return self._last_spinner_character

    def _write(self, msg, append_newline=True, err=False):
        if not self._active:
            return
        self._clear_last_job()
        if msg is not None:
            if append_newline:
                msg += "\n"
            write_to_stream(STDERR_WRITER if err else STDOUT_WRITER, msg)
        self._write_current_job()

    def _write_current_job(self):
        if self.jobs and TTY:
            line = "{} ".format(blue(self._spinner_character()))
            # must track line length manually as len() will count ANSI escape codes
            visible_length = 2
            try:
                progress = (self.progress / float(self.progress_total))
            except ZeroDivisionError:
                pass
            else:
                progress_text = "{:.1f}%  ".format(progress * 100)
                line += bold(progress_text)
                visible_length += len(progress_text)
            line += self.jobs[-1][:get_terminal_size().columns - 1 - visible_length]
            write_to_stream(STDOUT_WRITER, line)
            self._status_line_present = True


io = IOManager()
