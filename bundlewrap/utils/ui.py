from contextlib import contextmanager
from datetime import datetime
import fcntl
from functools import wraps
from multiprocessing import Event, Lock, Queue
import os
from signal import signal, SIGPIPE, SIG_DFL
import struct
import sys
import termios
from threading import Thread

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

    def activate_as_child(self, child_lock, child_finished, output_queue, status_line_cleared, stdin):
        self.parent_mode = False
        self.child_mode = True
        self.status_line_cleared = status_line_cleared
        self.child_lock = child_lock
        self.child_finished = child_finished
        self.output_queue = output_queue
        sys.stdin = stdin

    def activate_as_parent(self, debug=False):
        assert not self.child_mode
        self.debug_mode = debug
        self.jobs = []
        self.child_lock = Lock()
        self.child_finished = Event()
        self.parent_mode = True
        self.output_queue = Queue()
        self.status_line_cleared = Event()
        self.thread = Thread(target=self._print_thread)
        self.thread.daemon = True
        self.thread.start()

    def ask(self, question, default, epilogue=None, get_input=input_function):
        answers = _("[Y/n]") if default else _("[y/N]")
        question = question + " " + answers + " "
        with self.lock:
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
        return answer

    @contextmanager
    def capture(self):
        self.capture_mode = True
        self.captured_io = {
            'stderr': "",
            'stdout': "",
        }
        yield self.captured_io
        self.capture_mode = False

    @property
    def child_parameters(self):
        try:
            new_stdin = os.fdopen(os.dup(sys.stdin.fileno()))
        except ValueError:  # with pytest: redirected Stdin is pseudofile, has no fileno()
            new_stdin = sys.stdin
        return (
            self.child_lock,
            self.child_finished,
            self.output_queue,
            self.status_line_cleared,
            new_stdin,
        )

    @clear_formatting
    def debug(self, msg):
        self.output_queue.put({'msg': 'LOG', 'log_type': 'DBG', 'text': msg})

    def job_add(self, msg):
        self.output_queue.put({'msg': 'LOG', 'log_type': 'JOB_ADD', 'text': msg})

    def job_del(self, msg):
        self.output_queue.put({'msg': 'LOG', 'log_type': 'JOB_DEL', 'text': msg})

    @clear_formatting
    def stderr(self, msg):
        self.output_queue.put({'msg': 'LOG', 'log_type': 'ERR', 'text': msg})

    @clear_formatting
    def stdout(self, msg):
        self.output_queue.put({'msg': 'LOG', 'log_type': 'OUT', 'text': msg})

    @contextmanager
    def job(self, job_text):
        self.job_add(job_text)
        try:
            yield
        finally:
            self.job_del(job_text)

    @property
    @contextmanager
    def lock(self):
        with self.child_lock:
            # the child lock is required to make sure that only one
            # child can send the CLEAR command to the parent at the
            # same time
            self.child_finished.clear()
            self.output_queue.put({'msg': 'LOG', 'log_type': 'CLEAR'})
            # the CLEAR message tells the parent process to remove the
            # status line and we wait until it has done so
            self.status_line_cleared.wait()
            yield
            # we tell the parent process that it may continue
            self.child_finished.set()

    def _print_thread(self):
        assert self.parent_mode
        while True:
            msg = self.output_queue.get()
            if msg['log_type'] == 'QUIT':
                break
            if self.debug_mode and msg['log_type'] in ('OUT', 'DBG', 'ERR'):
                msg['text'] = datetime.now().strftime("[%Y-%m-%d %H:%M:%S.%f] ") + msg['text']
            if self.jobs and TTY:
                self._write("\r\033[K")
            if msg['log_type'] == 'OUT':
                self._write(msg['text'] + "\n")
            elif msg['log_type'] == 'ERR':
                self._write(msg['text'] + "\n", err=True)
            elif msg['log_type'] == 'DBG' and self.debug_mode:
                self._write(msg['text'] + "\n")
            elif msg['log_type'] == 'JOB_ADD' and TTY:
                self.jobs.append(msg['text'])
            elif msg['log_type'] == 'JOB_DEL' and TTY:
                self.jobs.remove(msg['text'])
            elif msg['log_type'] == 'CLEAR':
                # the process holding the outer lock should now be waiting for
                # us to remove any status lines present before it starts
                # printing
                self.status_line_cleared.set()
                # now we wait for the child process to complete its output
                self.child_finished.wait()

            if self.jobs and TTY:
                self.status_line_cleared.clear()
                self._write(inverse("{} ".format(self.jobs[-1])[:term_width() - 1]))

    def shutdown(self):
        assert self.parent_mode
        self.output_queue.put({'msg': 'LOG', 'log_type': 'QUIT'})
        self.thread.join()

    def _write(self, msg, err=False):
        write_to_stream(STDERR_WRITER if err else STDOUT_WRITER, msg)
        if self.capture_mode:
            self.captured_io['stderr' if err else 'stdout'] += msg


io = IOManager()
