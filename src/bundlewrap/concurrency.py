# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from datetime import datetime
from inspect import ismethod, isgenerator
from multiprocessing import Manager, Pipe, Process
import sys
from traceback import format_exception

from .exceptions import WorkerException
from .utils.text import force_text, mark_for_translation as _
from .utils.ui import io

JOIN_TIMEOUT = 5  # seconds


def _worker_process(wid, messages, pipe, io_params):
    """
    This is what actually runs in the child process.
    """
    # replace the child logger with one that will send logs back to the
    # parent process
    #from bundlewrap.utils import ui
    io.activate_as_child(*io_params)

    while True:
        # These two calls can block for an infinite amount of time. We
        # request work via the public queue and, eventually, some day,
        # we might get an answer via our private pipe.
        messages.put({'msg': 'REQUEST_WORK', 'wid': wid})
        msg = pipe.recv()
        if msg['msg'] == 'DIE':
            return
        elif msg['msg'] == 'NOOP':
            pass
        elif msg['msg'] == 'RUN':
            exception = None
            exception_task_id = None
            return_value = None
            start = datetime.now()
            traceback = None

            try:
                if msg['target_obj'] is None:
                    target = msg['target']
                else:
                    target = getattr(msg['target_obj'], msg['target'])

                return_value = target(*msg['args'], **msg['kwargs'])

                if isgenerator(return_value):
                    return_value = list(return_value)

            except Exception as e:
                if isinstance(e, WorkerException):
                    exception = e.wrapped_exception
                    exception_task_id = e.task_id
                else:
                    exception = force_text(repr(e))
                    exception_task_id = msg['task_id']
                traceback = "".join([force_text(line) for line in format_exception(*sys.exc_info())])
                return_value = None

            messages.put({
                'duration': datetime.now() - start,
                'exception': exception,
                'exception_task_id': exception_task_id,
                'msg': 'FINISHED_WORK',
                'return_value': return_value,
                'task_id': msg['task_id'],
                'traceback': traceback,
                'wid': wid,
            })


class WorkerPool(object):
    """
    Manages a bunch of worker processes.
    """
    def __init__(self, workers=4):
        if workers < 1:
            raise ValueError(_("at least one worker is required"))

        # A "worker" is simply a tuple consisting of a Process object
        # and our end of a pipe. Each worker is always adressed with
        # it's "worker id" (wid): That's the index of the tuple in
        # self.workers.
        self.workers = []

        # Lists of wids. idle_workers are those that are marked
        # explicitly as idle (don't confuse this with workers that
        # aren't processing a job right now).
        self.idle_workers = []
        self.workers_alive = list(range(workers))

        # We don't need to know *which* worker is currently processing a
        # job. We only need to know how many there are.
        self.jobs_open = 0

        # The public message queue. Workers ask for jobs here, report
        # finished work and log items.
        # Note: There's (at least) two ways to organize a pool like
        # this. One is to only open a pipe to each worker. Then, you can
        # use select() to see which pipe can be read from. Problem is,
        # this is not really supported by the multiprocessing module;
        # you have to dig into the internals and that's ugly. So, we go
        # for another option: A managed queue. Multiple processes can
        # write to it (all the workers do) and the parent can read from
        # it. However, this is only feasible when workers must talk to
        # the parent. The parent can't talk to the workers using this
        # queue. Thus, we still need a dedicated pipe to each worker
        # (see below).
        self.messages = Manager().Queue()

        for i in range(workers):
            (parent_conn, child_conn) = Pipe()
            p = Process(target=_worker_process,
                        args=(i, self.messages, child_conn, io.child_parameters))
            p.start()
            self.workers.append((p, parent_conn))

    def __enter__(self):
        return self

    def __exit__(self, type, value, traceback):
        self.shutdown()

    def get_event(self):
        """
        Blocks until a message from a worker is received.
        """
        msg = self.messages.get()
        if msg['msg'] == 'FINISHED_WORK':
            self.jobs_open -= 1
            # check for exception in child process and raise it
            # here in the parent
            if not msg['traceback'] is None:
                raise WorkerException(
                    msg['exception_task_id'],
                    msg['exception'],
                    msg['traceback'],
                )
        return msg

    def start_task(self, wid, target, task_id=None, args=None, kwargs=None):
        """
        wid         id of the worker to use
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

        if ismethod(target):
            target_obj = target.__self__
            target = target.__name__
        else:
            target_obj = None

        (process, pipe) = self.workers[wid]
        pipe.send({
            'msg': 'RUN',
            'task_id': task_id,
            'target': target,
            'target_obj': target_obj,
            'args': args,
            'kwargs': kwargs,
        })

        self.jobs_open += 1

    def mark_idle(self, wid):
        """
        Mark a worker as "idle".
        """
        # We don't really need to do something here. The worker will
        # simply keep blocking at his "pipe.read()". Just store his id
        # so we can answer him later.
        self.idle_workers.append(wid)

    def quit(self, wid):
        """
        Shutdown a worker.
        """
        (process, pipe) = self.workers[wid]
        try:
            pipe.send({'msg': 'DIE'})
        except IOError:
            pass
        pipe.close()
        process.join(JOIN_TIMEOUT)
        if process.is_alive():
            io.stderr(_(
                "worker process with PID {pid} didn't join "
                "within {time} seconds, terminating...").format(
                    pid=process.pid,
                    time=JOIN_TIMEOUT,
                )
            )
            process.terminate()
        self.workers_alive.remove(wid)

    def shutdown(self):
        """
        Shutdown all workers.
        """
        while self.workers_alive:
            self.quit(self.workers_alive[0])

    def activate_idle_workers(self):
        """
        Tell all idle workers to ask for work again.
        """
        for wid in self.idle_workers:
            # Send a noop to this worker. He will simply ask for new
            # work again.
            (process, pipe) = self.workers[wid]
            pipe.send({'msg': 'NOOP'})
        self.idle_workers = []

    def keep_running(self):
        """
        Returns True if this pool is not ready to die.
        """
        return self.jobs_open > 0 or self.workers_alive
