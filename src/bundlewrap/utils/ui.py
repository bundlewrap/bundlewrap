from codecs import getwriter
from contextlib import contextmanager
from datetime import datetime
from multiprocessing import Condition, Lock, Queue
from sys import stderr, stdout
from threading import Thread

from .text import ANSI_ESCAPE, mark_for_translation as _

try:
    STDOUT_WRITER = getwriter('utf-8')(stdout.buffer)
    STDERR_WRITER = getwriter('utf-8')(stderr.buffer)
except AttributeError:  # Python 2
    STDOUT_WRITER = getwriter('utf-8')(stdout)
    STDERR_WRITER = getwriter('utf-8')(stderr)
TTY = STDOUT_WRITER.isatty()

try:
    input_function = raw_input
except NameError:  # Python 3
    input_function = input


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

    def activate_as_child(self, output_lock, output_queue, status_line_cleared):
        self.parent_mode = False
        self.child_mode = True
        self.status_line_cleared = status_line_cleared
        self.output_lock = output_lock
        self.output_queue = output_queue

    def activate_as_parent(self, debug=False):
        assert not self.child_mode
        self.debug_mode = debug
        self.jobs = []
        self.output_lock = Lock()
        self.parent_mode = True
        self.output_queue = Queue()
        self.status_line_cleared = Condition()
        self.thread = Thread(target=self._print_thread)
        self.thread.daemon = True
        self.thread.start()

    def ask(self, question, default, get_input=input_function):
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
                    return True
                elif answer.lower() in (_("n"), _("no")) or (
                    not answer and not default
                ):
                    return False
                STDOUT_WRITER.write(_("Please answer with 'y(es)' or 'n(o)'.\n"))

    @property
    def child_parameters(self):
        return (self.output_lock, self.output_queue, self.status_line_cleared)

    def debug(self, msg):
        self.output_queue.put({'msg': 'LOG', 'log_type': 'DBG', 'text': msg})

    def job_add(self, msg):
        self.output_queue.put({'msg': 'LOG', 'log_type': 'JOB_ADD', 'text': msg})

    def job_del(self, msg):
        self.output_queue.put({'msg': 'LOG', 'log_type': 'JOB_DEL', 'text': msg})

    def stderr(self, msg):
        self.output_queue.put({'msg': 'LOG', 'log_type': 'ERR', 'text': msg})

    def stdout(self, msg):
        self.output_queue.put({'msg': 'LOG', 'log_type': 'OUT', 'text': msg})

    @contextmanager
    def job(self, job_text):
        self.job_add(job_text)
        yield
        self.job_del(job_text)

    @property
    @contextmanager
    def lock(self):
        with self.output_lock:
            self.status_line_cleared.wait()
            yield

    def _print_thread(self):
        assert self.parent_mode
        while True:
            if self.output_lock.acquire(False):
                msg = self.output_queue.get()
                if msg['log_type'] == 'QUIT':
                    break
                if self.debug_mode and msg['log_type'] in ('OUT', 'DBG', 'ERR'):
                    msg['text'] = datetime.now().strftime("[%Y-%m-%d %H:%M:%S.%f] ") + msg['text']
                if self.jobs and TTY:
                    write_to_stream(STDOUT_WRITER, "\r\033[K")
                if msg['log_type'] == 'OUT':
                    write_to_stream(STDOUT_WRITER, msg['text'] + "\n")
                elif msg['log_type'] == 'ERR':
                    write_to_stream(STDERR_WRITER, msg['text'] + "\n")
                elif msg['log_type'] == 'DBG' and self.debug_mode:
                    write_to_stream(STDOUT_WRITER, msg['text'] + "\n")
                elif msg['log_type'] == 'JOB_ADD' and TTY:
                    self.jobs.append(msg['text'])
                elif msg['log_type'] == 'JOB_DEL' and TTY:
                    self.jobs.remove(msg['text'])
                if self.jobs and TTY:
                    write_to_stream(STDOUT_WRITER, "[status] " + self.jobs[0])
                self.output_lock.release()
            else:  # someone else is holding the output lock
                # the process holding the lock should now be waiting for
                # us to remove any status lines present before it starts
                # printing
                if self.jobs and TTY:
                    write_to_stream(STDOUT_WRITER, "\r\033[K")
                self.status_line_cleared.notify()
                # now we wait until the other process has finished and
                # released the output lock
                self.output_lock.acquire()
                self.output_lock.release()

    def shutdown(self):
        assert self.parent_mode
        self.output_queue.put({'msg': 'LOG', 'log_type': 'QUIT'})
        self.thread.join()


io = IOManager()
