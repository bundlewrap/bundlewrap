from time import sleep
from unittest import TestCase

from mock import MagicMock, patch

from blockwart.concurrency import Logger, Worker, WorkerPool
from blockwart.exceptions import WorkerException


class LoggerTest(TestCase):
    """
    Tests blockwart.concurrency.Logger.
    """
    def test_put(self):
        queue = MagicMock()
        l = Logger(queue)
        l.critical(1)
        queue.put.assert_called_once_with(('critical', 1))
        l.debug(2)
        queue.put.assert_called_with(('debug', 2))
        l.error(3)
        queue.put.assert_called_with(('error', 3))
        l.info(4)
        queue.put.assert_called_with(('info', 4))
        l.warning(5)
        queue.put.assert_called_with(('warning', 5))

    def test_logged_lines(self):
        def task():
            from blockwart.utils import LOG
            LOG.debug(1)
            LOG.info(2)
            sleep(.01)
            LOG.warning(3)
            sleep(.01)
            LOG.error(4)
            LOG.critical(5)
            return None

        w = Worker()
        logs = []
        w.start_task(task)
        while w.is_busy:
            logs += list(w.logged_lines)
        logs += list(w.logged_lines)
        self.assertEqual(
            logs,
            [('debug', 1), ('info', 2), ('warning', 3), ('error', 4),
             ('critical', 5)],
        )
        w.reap()

    def test_logger_redirection(self):
        def task():
            from blockwart.utils import LOG
            LOG.debug("ohai")
            return None

        with patch('blockwart.utils.LOG') as PATCHED_LOG:
            w = Worker()
            w.start_task(task)
            w.reap()

        PATCHED_LOG.debug.assert_called_once_with("ohai")


class WorkerTest(TestCase):
    """
    Tests blockwart.concurrency.Worker.
    """
    def test_exception(self):
        def myfunc():
            raise Exception()

        w = Worker()
        w.start_task(myfunc)
        with self.assertRaises(WorkerException):
            w.reap()

    def test_generator(self):
        def myfunc():
            return xrange(47)

        w = Worker()
        w.start_task(myfunc)
        r = w.reap()
        self.assertEqual(list(xrange(47)), list(r))

    def test_is_busy(self):
        w = Worker()
        w.start_task(sleep, args=(.01,))
        self.assertTrue(w.is_busy)
        sleep(.02)
        self.assertFalse(w.is_busy)

    def test_init_not_busy(self):
        w = Worker()
        self.assertFalse(w.is_busy)

    def test_method_call(self):
        class MyClass(object):
            def __init__(self, state):
                self.state = state

            def mymethod(self, param):
                return self.state + param

        obj = MyClass(40)
        w = Worker()
        w.start_task(obj.mymethod, args=(7,))
        self.assertEqual(w.reap(), 47)

    def test_method_call_immutable(self):
        class MyClass(object):
            def __init__(self, state):
                self.state = state

            def mymethod(self, param):
                self.state = param

        obj = MyClass(47)
        w = Worker()
        w.start_task(obj.mymethod, args=(42,))
        w.reap()
        self.assertEqual(obj.state, 47)

    def test_result(self):
        w = Worker()
        w.start_task(lambda: 47)
        self.assertEqual(w.reap(), 47)
        w.start_task(lambda: 48)
        self.assertEqual(w.reap(), 48)


class WorkerPoolTest(TestCase):
    """
    Tests blockwart.concurrency.WorkerPool.
    """
    def test_init(self):
        with self.assertRaises(ValueError):
            WorkerPool(workers=0)
        with self.assertRaises(ValueError):
            WorkerPool(workers=-1)
        WorkerPool(workers=1)

    def test_get_idle_worker(self):
        class MockWorker(object):
            def __init__(self):
                self.busy_counter = 0
                self.is_reapable = False
                self.result = None

            @property
            def is_busy(self):
                self.busy_counter += 1
                return self.busy_counter != 47

        with patch('blockwart.concurrency.Worker', new=MockWorker):
            p = WorkerPool(workers=2)
            for i in xrange(2):
                w = p.get_idle_worker()
                self.assertEqual(w.busy_counter, 47)
