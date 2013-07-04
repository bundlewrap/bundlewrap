from multiprocessing import Process, Queue
from Queue import Empty
from time import sleep


def _queue_helper(queue, target, args, kwargs):
    queue.put(target(*args, **kwargs))


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

    def _get_result(self, block=True):
        if not self.started:
            return
        try:
            self._result = self.queue.get(block=block)
            self.process.join()
        except Empty:
            pass

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
        self.queue = Queue()
        self.process = Process(
            target=_queue_helper,
            args=(self.queue, target, args, kwargs),
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
            sleep(.01)

    def get_reapable_worker(self):
        """
        Return a worker that can be .reap()ed. None if no worker is
        ready.
        """
        for worker in self.workers:
            if worker.is_reapable:
                return worker
        return None
