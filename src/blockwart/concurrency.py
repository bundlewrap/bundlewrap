from inspect import ismethod, isgenerator
from logging import getLogger, Handler
from multiprocessing import Manager, Pipe, Process
from os import dup, fdopen
import sys
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
    def __init__(self, messages):
        Handler.__init__(self)
        self.messages = messages

    def emit(self, record):
        self.messages.put({'msg': 'LOG_ENTRY', 'log_entry': record})


def _patch_logger(logger, new_handler=None):
    for handler in logger.handlers:
        logger.removeHandler(handler)
    if new_handler is not None:
        logger.addHandler(new_handler)
    logger.setLevel(0)


def _worker_process(wid, messages, pipe, stdin=None):
    """
    This is what actually runs in the child process.
    """
    if stdin is not None:
        # replace stdin with the one our parent gave us
        sys.stdin = stdin

    # replace the child logger with one that will send logs back to the
    # parent process
    from blockwart import utils
    child_log_handler = ChildLogHandler(messages)
    _patch_logger(getLogger(), child_log_handler)
    _patch_logger(utils.LOG)

    while True:
        messages.put({'msg': 'REQUEST_WORK', 'wid': wid})
        msg = pipe.recv()
        if msg['msg'] == 'DIE':
            # clean up Fabric connections first...
            disconnect_all()
            # then die
            return
        elif msg['msg'] == 'NOOP':
            pass
        elif msg['msg'] == 'RUN':
            try:
                if msg['target_obj'] is None:
                    target = msg['target']
                else:
                    target = getattr(msg['target_obj'], msg['target'])

                traceback = None
                return_value = target(*msg['args'], **msg['kwargs'])

                if isgenerator(return_value):
                    return_value = list(return_value)
            except Exception:
                traceback = "".join(format_exception(*sys.exc_info()))
                return_value = None
            finally:
                messages.put({'msg': 'FINISHED_WORK',
                              'wid': wid,
                              'task_id': msg['task_id'],
                              'return_value': return_value,
                              'traceback': traceback})


class WorkerPool(object):
    """
    Manages a bunch of Worker instances.
    """
    def __init__(self, workers=4):
        if workers < 1:
            raise ValueError(_("at least one worker is required"))
        self.workers = []
        self.idle_workers = []
        self.jobs_open = 0
        self.workers_alive = range(workers)
        self.messages = Manager().Queue()
        stdin = fdopen(dup(sys.stdin.fileno())) if workers == 1 else None
        for i in xrange(workers):
            (parent_conn, child_conn) = Pipe()
            p = Process(target=_worker_process,
                        args=(i, self.messages, child_conn, stdin,))
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
            if not msg['traceback'] is None:
                # check for exception in child process and raise it
                # here in the parent
                raise WorkerException(msg['traceback'])
        elif msg['msg'] == 'LOG_ENTRY':
            LOG.handle(msg['log_entry'])
        return msg

    def start_task(self, wid, target, task_id=None, args=None, kwargs=None):
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

        if ismethod(target):
            target_obj = target.im_self
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

        # The worker will simply keep blocking at his "pipe.read()".
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
            LOG.warn(_(
                "worker process with PID {} didn't join "
                "within {} seconds, terminating...").format(
                    process.pid,
                    JOIN_TIMEOUT,
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
        for wid in self.idle_workers:
            # Send a noop to this worker. He will simply ask for new
            # work again.
            (process, pipe) = self.workers[wid]
            pipe.send({'msg': 'NOOP'})
        self.idle_workers = []

    def keep_running(self):
        return self.jobs_open > 0 or self.workers_alive
