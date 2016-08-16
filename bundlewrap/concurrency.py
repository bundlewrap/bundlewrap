# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from concurrent.futures import ThreadPoolExecutor, wait, FIRST_COMPLETED
from datetime import datetime
from random import randint
from sys import exit
from traceback import format_tb

from .utils.text import mark_for_translation as _
from .utils.ui import io, QUIT_EVENT

JOIN_TIMEOUT = 5  # seconds


class WorkerPool(object):
    """
    Manages a bunch of worker threads.
    """
    def __init__(
        self,
        tasks_available,
        next_task,
        handle_result=None,
        handle_exception=None,
        pool_id=None,
        workers=4,
    ):
        if workers < 1:
            raise ValueError(_("at least one worker is required"))

        self.tasks_available = tasks_available
        self.next_task = next_task
        self.handle_result = handle_result
        self.handle_exception = handle_exception

        self.number_of_workers = workers
        self.idle_workers = set(range(self.number_of_workers))

        self.pool_id = "unnamed_pool_{}".format(randint(1, 99999)) if pool_id is None else pool_id
        self.pending_futures = {}

    def _get_result(self):
        """
        Blocks until a result from a worker is received.
        """
        io.debug(_("worker pool {pool} waiting for next task to complete").format(
            pool=self.pool_id,
        ))
        while True:
            # we must use a timeout here to allow Python <3.3 to call
            # its SIGINT handler
            # see also http://stackoverflow.com/q/25676835
            completed, pending = wait(
                self.pending_futures.keys(),
                return_when=FIRST_COMPLETED,
                timeout=0.1,
            )
            if completed:
                break
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
            if not hasattr(exception, '__traceback__'):  # Python 2
                exception.__traceback__ = future.exception_info()[1]
            exception.__task_id = task_id
            raise exception
        else:
            io.debug(_(
                "worker pool {pool} delivering result of {task} on worker #{worker}"
            ).format(
                pool=self.pool_id,
                task=task_id,
                worker=worker_id,
            ))
            return (task_id, future.result(), datetime.now() - start_time)

    def start_task(self, target=None, task_id=None, args=None, kwargs=None):
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

    def run(self):
        io.debug(_("spinning up worker pool {pool}").format(pool=self.pool_id))
        processed_results = []
        exit_code = 0
        self.executor = ThreadPoolExecutor(max_workers=self.number_of_workers)
        try:
            while (
                (self.tasks_available() and not QUIT_EVENT.is_set()) or
                self.workers_are_running
            ):
                while (
                    self.tasks_available() and
                    self.workers_are_available and
                    not QUIT_EVENT.is_set()
                ):
                    task = self.next_task()
                    if task is not None:
                        self.start_task(**task)

                if self.workers_are_running:
                    try:
                        result = self._get_result()
                    except SystemExit as exc:
                        exit_code = exc.code
                        # just make sure QUIT_EVENT is set and continue
                        # waiting for pending results
                        QUIT_EVENT.set()
                    except Exception as exc:
                        traceback = "".join(format_tb(exc.__traceback__))
                        if self.handle_exception is None:
                            raise exc
                        else:
                            processed_results.append(
                                self.handle_exception(exc.__task_id, exc, traceback)
                            )
                    else:
                        if self.handle_result is not None:
                            processed_results.append(self.handle_result(*result))
            if QUIT_EVENT.is_set():
                # we have reaped all our workers, let's stop this thread
                # before it does anything else
                exit(exit_code)
            return processed_results
        finally:
            io.debug(_("shutting down worker pool {pool}").format(pool=self.pool_id))
            self.executor.shutdown()
            io.debug(_("worker pool {pool} has been shut down").format(pool=self.pool_id))

    @property
    def workers_are_available(self):
        return bool(self.idle_workers)

    @property
    def workers_are_running(self):
        return bool(self.pending_futures)
