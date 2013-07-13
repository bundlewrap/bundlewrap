from multiprocessing import Process, Queue
from Queue import Empty
from sys import exc_info
from time import sleep
from traceback import format_exception

from .exceptions import WorkerException


class Logger(object):
    def __init__(self, queue):
        self.queue = queue

    def critical(self, msg):
        self.queue.put(('critical', msg))

    def debug(self, msg):
        self.queue.put(('debug', msg))

    def error(self, msg):
        self.queue.put(('error', msg))

    def info(self, msg):
        self.queue.put(('info', msg))

    def warning(self, msg):
        self.queue.put(('warning', msg))


def _queue_helper(queue_logger, queue_result, target, args, kwargs):
    from blockwart import utils
    utils.LOG = Logger(queue_logger)
    try:
        result = target(*args, **kwargs)
    except Exception as e:
        traceback = "".join(format_exception(*exc_info()))
        result = (e, traceback)
    finally:
        queue_result.put(result)


class Worker(object):
    """
    Manages a background worker process.
    """
    def __init__(self):
        self.started = False

    @property
    def is_busy(self):
        """
        False if self.result can be obtained directly without blocking.
        """
        return self.started and not self.is_reapable

    @property
    def is_reapable(self):
        self._get_result(block=False)
        return hasattr(self, '_result')

    @property
    def logged_lines(self):
        while True:
            try:
                yield self.queue_logger.get(block=False)
            except Empty:
                break

    def _get_result(self, block=True):
        if not self.started:
            return
        try:
            self._result = self.queue_result.get(block=block)
            self.process.join()
            if (
                isinstance(self._result, tuple) and
                len(self._result) == 2 and
                isinstance(self._result[0], Exception)
            ):
                # check for exception in child process and raise it
                # here in the parent
                raise WorkerException(self._result[0], self._result[1])
        except Empty:
            pass

    def log(self):
        if not self.started:
            return
        from blockwart.utils import LOG
        for level, msg in self.logged_lines:
            getattr(LOG, level)(msg)

    def reap(self):
        """
        Block until the result of this worker can be returned.

        The worker is then reset, reap() cannot be called again until
        another task has been started.
        """
        while not self.is_reapable:
            sleep(.01)
        r = self._result
        self.log()
        self.reset()
        return r

    def reset(self):
        self.id = None
        self.started = False
        if hasattr(self, '_result'):
            delattr(self, '_result')

    def start_task(self, target, id=None, args=None, kwargs=None):
        """
        target      any callable (includes bound methods)
        id          something to remember this worker by
        args        list of positional arguments passed to target
        kwargs      dictionary of keyword arguments passed to target
        """
        if args is None:
            args = ()
        if kwargs is None:
            kwargs = {}

        self.id = id
        self.queue_logger = Queue()
        self.queue_result = Queue()
        self.process = Process(
            target=_queue_helper,
            args=(self.queue_logger, self.queue_result, target, args, kwargs),
        )
        self.started = True
        self.process.start()


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

    def wait(self, amount=0.01):
        """
        Just a convenience wrapper around time.sleep.
        """
        sleep(amount)
