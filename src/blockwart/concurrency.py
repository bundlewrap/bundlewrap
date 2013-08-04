from inspect import ismethod
from logging import getLogger, Handler
from multiprocessing import Manager, Pipe, Process
from os import dup, fdopen
import sys
from time import sleep
from traceback import format_exception

from fabric.network import disconnect_all

from .exceptions import WorkerException
from .utils import LOG
from .utils.text import mark_for_translation as _

JOIN_TIMEOUT = 5


class ChildLogHandler(Handler):
    """
    Captures log events in child processes and inserts them into the
    queue to be processed by the parent process.
    """
    def __init__(self, queue):
        Handler.__init__(self)
        self.queue = queue

    def emit(self, record):
        self.queue.put(record)


def _patch_logger(logger, new_handler=None):
    for handler in logger.handlers:
        logger.removeHandler(handler)
    if new_handler is not None:
        logger.addHandler(new_handler)
    logger.setLevel(0)


def _worker_process(pipe, log_queue, stdin, interactive=False):
    """
    This is what actually runs in the child process.
    """
    if interactive:
        # replace stdin with the one our parent gave us
        sys.stdin = stdin

    # replace the child logger with one that will send logs back to the
    # parent process
    from blockwart import utils
    child_log_handler = ChildLogHandler(log_queue)
    _patch_logger(getLogger(), child_log_handler)
    _patch_logger(utils.LOG)

    while True:
        if not pipe.poll(.01):
            continue
        message = pipe.recv()
        if message['order'] == 'die':
            # clean up Fabric connections first...
            disconnect_all()
            # then die
            return
        else:
            try:
                if message['target_obj'] is None:
                    target = message['target']
                else:
                    target = getattr(message['target_obj'], message['target'])

                result = {
                    'raised_exception': False,
                    'return_value': target(
                        *message['args'],
                        **message['kwargs']
                    ),
                }
            except Exception:
                traceback = "".join(format_exception(*sys.exc_info()))
                result = {
                    'raised_exception': True,
                    'traceback': traceback,
                }
            finally:
                pipe.send(result)


class Worker(object):
    """
    Manages a background worker process.
    """
    def __init__(self, interactive=False):
        self.id = None
        self.started = False
        self.log_queue = Manager().Queue()
        self.pipe, child_pipe = Pipe()
        child_stdin = fdopen(dup(sys.stdin.fileno()))
        self.process = Process(
            target=_worker_process,
            args=(child_pipe, self.log_queue, child_stdin, interactive),
        )
        self.process.start()

    def __enter__(self):
        return self

    def __exit__(self, type, value, traceback):
        self.shutdown()

    @property
    def is_busy(self):
        """
        False when self.reap() can return directly without blocking.
        """
        return self.started and not self.is_reapable

    @property
    def is_reapable(self):
        """
        True when the child process has finished a task.
        """
        self._get_result()
        return hasattr(self, '_result')

    def _get_result(self):
        if not self.started:
            return

        while not self.log_queue.empty():
            LOG.handle(self.log_queue.get())

        if self.pipe.poll():
            self._result = self.pipe.recv()
            if self._result['raised_exception']:
                # check for exception in child process and raise it
                # here in the parent
                raise WorkerException(self._result['traceback'])

    def reap(self):
        """
        Block until the result of this worker can be returned.

        The worker is then reset, reap() cannot be called again until
        another task has been started.
        """
        while not self.is_reapable:
            sleep(.01)
        r = self._result
        self.reset()
        return r['return_value']

    def reset(self):
        self.id = None
        self.started = False
        if hasattr(self, '_result'):
            delattr(self, '_result')

    def shutdown(self):
        try:
            self.pipe.send({'order': 'die'})
        except IOError:
            pass
        self.pipe.close()
        self.process.join(JOIN_TIMEOUT)
        if self.process.is_alive():
            LOG.warn(_(
                "worker process with ID '{}' and PID {} didn't join "
                "within {} seconds, terminating...").format(
                    self.id,
                    self.process.pid,
                    JOIN_TIMEOUT,
                )
            )
            self.process.terminate()

    def start_task(self, target, id=None, args=None, kwargs=None):
        """
        target      any callable (includes bound methods)
        id          something to remember this worker by
        args        list of positional arguments passed to target
        kwargs      dictionary of keyword arguments passed to target
        """
        if args is None:
            args = []
        else:
            args = list(args)
        if kwargs is None:
            kwargs = {}

        if ismethod(target):
            target_obj = target.im_self
            target = target.__name__
        else:
            target_obj = None

        self.id = id
        self.pipe.send({
            'order': 'run',
            'target': target,
            'target_obj': target_obj,
            'args': args,
            'kwargs': kwargs,
        })
        self.started = True


class WorkerPool(object):
    """
    Manages a bunch of Worker instances.
    """
    def __init__(self, workers=4, interactive=False):
        self.workers = []
        if workers < 1:
            raise ValueError("at least one worker is required")
        for i in xrange(workers):
            self.workers.append(Worker(interactive=interactive))

    def __enter__(self):
        return self

    def __exit__(self, type, value, traceback):
        self.shutdown()

    @property
    def busy_count(self):
        count = 0
        for worker in self.workers:
            if worker.is_busy:
                count += 1
        return count

    @property
    def reapable_count(self):
        count = 0
        for worker in self.workers:
            if worker.is_reapable:
                count += 1
        return count

    def get_idle_worker(self, block=True):
        """
        Returns an idle worker. If block is True, this will block until
        there is a worker available. Otherwise, None will be returned.
        """
        while True:
            for worker in self.workers:
                if not worker.is_busy and not worker.is_reapable:
                    return worker
            if not block:
                return None
            self.wait()

    def get_reapable_worker(self):
        """
        Return a worker that can be .reap()ed. None if no worker is
        ready.
        """
        for worker in self.workers:
            if worker.is_reapable:
                return worker
        return None

    def shutdown(self):
        for worker in self.workers:
            worker.shutdown()

    def wait(self, amount=0.01):
        """
        Just a convenience wrapper around time.sleep.
        """
        sleep(amount)
