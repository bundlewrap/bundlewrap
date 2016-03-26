# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from concurrent.futures import ThreadPoolExecutor, wait, FIRST_COMPLETED
from datetime import datetime
from random import randint

from .exceptions import WorkerException
from .utils.text import mark_for_translation as _
from .utils.ui import io

JOIN_TIMEOUT = 5  # seconds


class WorkerPool(object):
    """
    Manages a bunch of worker threads.
    """
    def __init__(self, pool_id=None, workers=4):
        if workers < 1:
            raise ValueError(_("at least one worker is required"))

        self.number_of_workers = workers
        self.idle_workers = set(range(self.number_of_workers))

        self.pool_id = "unnamed_pool_{}".format(randint(1, 99999)) if pool_id is None else pool_id
        self.pending_futures = {}

    def __enter__(self):
        io.debug(_("spinning up worker pool {pool}").format(pool=self.pool_id))
        self.executor = ThreadPoolExecutor(max_workers=self.number_of_workers)
        return self

    def __exit__(self, type, value, traceback):
        io.debug(_("shutting down worker pool {pool}").format(pool=self.pool_id))
        self.executor.shutdown()
        io.debug(_("worker pool {pool} has been shut down").format(pool=self.pool_id))

    def get_result(self):
        """
        Blocks until a result from a worker is received.
        """
        io.debug(_("worker pool {pool} waiting for next task to complete").format(
            pool=self.pool_id,
        ))
        completed, pending = wait(self.pending_futures.keys(), return_when=FIRST_COMPLETED)
        future = completed.pop()

        start_time = self.pending_futures[future]['start_time']
        task_id = self.pending_futures[future]['task_id']
        worker_id = self.pending_futures[future]['worker_id']

        del self.pending_futures[future]
        self.idle_workers.add(worker_id)

        exception = future.exception()
        if exception:
            io.debug(_(
                "exception raised while executing task {task} on worker #{worker} "
                "of worker pool {pool}"
            ).format(
                pool=self.pool_id,
                task=task_id,
                worker=worker_id,
            ))
            raise WorkerException(exception, task_id=task_id, worker_id=worker_id)
        else:
            io.debug(_(
                "worker pool {pool} delivering result of {task} on worker #{worker}"
            ).format(
                pool=self.pool_id,
                task=task_id,
                worker=worker_id,
            ))
            return {
                'duration': datetime.now() - start_time,
                'return_value': future.result(),
                'task_id': task_id,
                'worker_id': worker_id,
            }

    def start_task(self, target, task_id=None, args=None, kwargs=None):
        """
        target      any callable (includes bound methods)
        task_id     something to remember this worker by
        args        list of positional arguments passed to target
        kwargs      dictionary of keyword arguments passed to target
        """
        if args is None:
            args = []
        else:
            args = list(args)
        if kwargs is None:
            kwargs = {}

        task_id = "unnamed_task_{}".format(randint(1, 99999)) if task_id is None else task_id
        worker_id = self.idle_workers.pop()

        io.debug(_("worker pool {pool} is starting task {task} on worker #{worker}").format(
            pool=self.pool_id,
            task=task_id,
            worker=worker_id,
        ))
        self.pending_futures[self.executor.submit(target, *args, **kwargs)] = {
            'start_time': datetime.now(),
            'task_id': task_id,
            'worker_id': worker_id,
        }

    @property
    def workers_are_available(self):
        return bool(self.idle_workers)

    @property
    def workers_are_running(self):
        return bool(self.pending_futures)
