from multiprocessing import Process, Queue
from Queue import Empty
from time import sleep


class Worker(object):
    """
    Manages a background worker process.
    """
    def __init__(self):
        self.started = False

    def _get_result(self, block=True):
        try:
            self._result = self.queue.get(block=block)
            self.process.join()
        except Empty:
            pass

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
        if hasattr(self, '_result'):
            delattr(self, '_result')
        self.id = id
        self.queue = Queue()
        self.process = Process(
            target=lambda: self.queue.put(target(*args, **kwargs))
        )
        self.started = True
        self.process.start()

    @property
    def is_busy(self):
        """
        False if self.result can be obtained directly without blocking.
        """
        if not self.started:
            return False
        self._get_result(block=False)
        return not hasattr(self, '_result')

    @property
    def result(self):
        if not self.started:
            return None
        if hasattr(self, '_result'):
            return self._result
        else:
            self._get_result(block=True)
            return self._result


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

    def get_idle_worker(self):
        """
        Blocks until there is a worker available.

        You will probably want to check that workers .id and .result
        properties to get
        """
        while True:
            for worker in self.workers:
                if not worker.is_busy:
                    return worker
            sleep(.01)
