from inspect import ismethod
from logging import Handler
from multiprocessing import Manager, Pipe, Process
from sys import exc_info
from time import sleep
from traceback import format_exception

from .exceptions import WorkerException
from .utils import LOG


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


def _worker_process(pipe, log_queue):
    """
    This is what actually runs in the child process.
    """
    # replace the child logger with one that will send logs back to the
    # parent process
    from blockwart import utils
    for handler in utils.LOG.handlers:
        assert not isinstance(handler, ChildLogHandler)
        utils.LOG.removeHandler(handler)
    handler = ChildLogHandler(log_queue)
    utils.LOG.addHandler(handler)
    utils.LOG.setLevel(0)

    while True:
        if not pipe.poll(.01):
            continue
        message = pipe.recv()
        if message['order'] == 'die':
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
            except Exception as e:
                traceback = "".join(format_exception(*exc_info()))
                result = {
                    'raised_exception': True,
                    'exception': e,
                    'traceback': traceback,
                }
            finally:
                pipe.send(result)


class Worker(object):
    """
    Manages a background worker process.
    """
    def __init__(self):
        self.id = None
        self.started = False
        self.log_queue = Manager().Queue()
        self.pipe, child_pipe = Pipe()
        self.process = Process(
            target=_worker_process,
            args=(child_pipe, self.log_queue),
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
                raise WorkerException(
                    self._result['exception'],
                    self._result['traceback'],
                )

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
        self.process.join()

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
    def __init__(self, workers=4):
        self.workers = []
        if workers < 1:
            raise ValueError("at least one worker is required")
        for i in xrange(workers):
            self.workers.append(Worker())

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
