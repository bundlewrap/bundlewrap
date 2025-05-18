from contextlib import contextmanager, suppress
from datetime import datetime, timedelta
import faulthandler
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
    trim_visible_len_to,
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
            msg = f"[{datetime.now().isoformat()}] {msg}"
        return f(self, msg, **kwargs)
    return wrapped


def capture_for_debug_logfile(f):
    @wraps(f)
    def wrapped(self, msg, **kwargs):
        if self.debug_log_file and self._active:
            with self.lock:
                clean_msg = ansi_clean(msg).rstrip("\n")
                self.debug_log_file.write(
                    f"[{datetime.now().isoformat()}] {clean_msg}\n"
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
        faulthandler.dump_traceback()


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


def write_to_stream(stream, msg, flush=True):
    with suppress(BrokenPipeError):
        if TTY:
            stream.write(msg)
        else:
            stream.write(ansi_clean(msg))

        if flush:
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


class JobManager:
    def __init__(self):
        self._jobs = []

    def add(self, msg):
        job_id = (time(), msg)
        self._jobs.append(job_id)
        return job_id

    def remove(self, job_id):
        self._jobs.remove(job_id)

    @property
    def current_job(self):
        try:
            job_start, job_msg = self._jobs[-1]
        except IndexError:
            return None
        current_time = time()
        if current_time - job_start > 3.0:
            # If the latest job is taking a long time, start rotating
            # the displayed job every 3s. That way, users can see all
            # long-running jobs currently in progress.
            index = int(current_time / 3.0) % len(self._jobs)
            job_start, job_msg = self._jobs[index]

        elapsed = current_time - job_start
        if elapsed > 10.0:
            job_msg += " ({})".format(format_duration(timedelta(seconds=elapsed)))

        return job_msg

    @property
    def messages(self):
        return [job_msg for job_start, job_msg in self._jobs]


class IOManager:
    """
    Threadsafe singleton class that handles all IO.
    """
    def __init__(self):
        self._active = False
        self.debug_log_file = None
        self.debug_mode = False
        self.jobs = JobManager()
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

    def __enter__(self):
        self.activate()
        # return self, so users could also do `with IOManager() as io:`
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        self.deactivate()

    def activate(self):
        if self._active:
            return

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
        self._original_sigint_handler = signal(SIGINT, sigint_handler)
        self._original_sigquit_handler = signal(SIGQUIT, sigquit_handler)
        faulthandler.enable()
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
            self._clear_last_job(flush=False)
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
        if not self._active:
            return

        self._active = False
        if TTY:
            write_to_stream(STDOUT_WRITER, SHOW_CURSOR)
        signal(SIGINT, self._original_sigint_handler)
        signal(SIGQUIT, self._original_sigint_handler)
        faulthandler.disable()
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
            self._clear_last_job(flush=False)
            job_id = self.jobs.add(msg)
            self._write_current_job()
            return job_id

    def job_del(self, job_id):
        if not self._active:
            return
        with self.lock:
            self._clear_last_job(flush=False)
            self.jobs.remove(job_id)
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
            if self.jobs.messages:
                table.append([bold(_("Running jobs")), self.jobs.messages[0].strip()])
                for job in self.jobs.messages[1:]:
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
        job_id = self.job_add(job_text)
        try:
            yield
        finally:
            self.job_del(job_id)

    def job_wrapper(self, job_text):
        def outer_wrapper(wrapped_function):
            @wraps(wrapped_function)
            def inner_wrapper(*args, **kwargs):
                with self.job(job_text.format(*args, **kwargs)):
                    return wrapped_function(*args, **kwargs)
            return inner_wrapper
        return outer_wrapper

    def _clear_last_job(self, flush=True):
        if self._status_line_present and TTY:
            # Some terminals respond very quickly to \e[K: They
            # immediately clear the line and redraw their screen right
            # away, which means an empty line is visible for a brief
            # moment. It takes some (short amount of) time until we
            # write the next line. This means we alternate between
            # "empty line" and "line with text", which means:
            # Flickering.
            #
            # We can avoid this to some degree by not flushing stdout
            # after writing \e[K.
            #
            # We can only do this if we know for certain that we will
            # write more data soon. For example, this is the case when
            # _clear_last_job() is followed by _write_current_job().
            #
            # It is *not* possible to always omit the flush. Sometimes,
            # _clear_last_job() is called before _write(..., err=True),
            # meaning the first call writes to stdout and the second one
            # to stderr. This results in garbled output because the \e[K
            # is still lingering in the buffer for stdout.
            #
            # Note to future readers: If this causes issues and it's too
            # hard to understand, then simply remove the 'flush' flag
            # and go back to always flushing the buffers. This is mostly
            # a cosmetic issue and it's better to have some flickering
            # than completely garbled output.
            write_to_stream(STDOUT_WRITER, "\r\033[K", flush=flush)
            self._status_line_present = False

    def _signal_handler_thread_body(self):
        while self._active:
            self.progress_show()
            if not self._waiting_for_input:  # do not block and ignore SIGINT while .ask()ing
                with self.lock:
                    self._clear_last_job(flush=False)
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
                    _exit(130)  # https://tldp.org/LDP/abs/html/exitcodes.html
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
        current_job = self.jobs.current_job
        if TTY:
            if current_job:
                line = "{} ".format(blue(self._spinner_character()))
                try:
                    progress = (self.progress / float(self.progress_total))
                except ZeroDivisionError:
                    pass
                else:
                    progress_text = "{:.1f}%  ".format(progress * 100)
                    line += bold(progress_text)
                line += current_job
                write_to_stream(
                    STDOUT_WRITER,
                    trim_visible_len_to(line, get_terminal_size().columns),
                )
                self._status_line_present = True
            else:
                # If there are jobs to be displayed, the call above to
                # write_to_stream() will flush stdout. But if there are
                # none, then a \e[K might still be lingering in the
                # buffer. See comment in _clear_last_job().
                STDOUT_WRITER.flush()


io = IOManager()
