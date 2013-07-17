from time import sleep
from unittest import TestCase

from mock import MagicMock, patch

from blockwart.concurrency import Logger, Worker, WorkerPool
from blockwart.exceptions import WorkerException


def _log_task():
    from blockwart.utils import LOG
    LOG.debug(1)
    LOG.info(2)
    LOG.warning(3)
    LOG.error(4)
    LOG.critical(5)
    return None


class LoggerTest(TestCase):
    """
    Tests blockwart.concurrency.Logger.
    """
    def test_send(self):
        pipe = MagicMock()
        l = Logger(pipe)
        l.critical(1)
        pipe.send.assert_called_once_with(
            {'log_level': 'critical', 'log_msg': 1}
        )
        l.debug(2)
        pipe.send.assert_called_with(
            {'log_level': 'debug', 'log_msg': 2}
        )
        l.error(3)
        pipe.send.assert_called_with(
            {'log_level': 'error', 'log_msg': 3}
        )
        l.info(4)
        pipe.send.assert_called_with(
            {'log_level': 'info', 'log_msg': 4}
        )
        l.warning(5)
        pipe.send.assert_called_with(
            {'log_level': 'warning', 'log_msg': 5}
        )

    def test_logger_redirection(self):
        with patch('blockwart.utils.LOG') as PATCHED_LOG:
            with Worker() as w:
                w.start_task(_log_task)
                w.reap()

        PATCHED_LOG.debug.assert_called_once_with(1)
        PATCHED_LOG.info.assert_called_once_with(2)
        PATCHED_LOG.warning.assert_called_once_with(3)
        PATCHED_LOG.error.assert_called_once_with(4)
        PATCHED_LOG.critical.assert_called_once_with(5)


def _raise_exception():
    raise Exception()


def _return_generator():
    return xrange(47)


class _MethodCallTestClass(object):
    def __init__(self, state):
        self.state = state

    def mymethod(self, param):
        return self.state + param


class _ImmutableTestClass(object):
    def __init__(self, state):
        self.state = state

    def mymethod(self, param):
        self.state = param


def _fourtyseven():
    return 47


def _fourtyeight():
    return 48


class WorkerTest(TestCase):
    """
    Tests blockwart.concurrency.Worker.
    """
    def test_exception(self):
        with Worker() as w:
            w.start_task(_raise_exception)
            with self.assertRaises(WorkerException):
                w.reap()

    def test_generator(self):
        with Worker() as w:
            w.start_task(_return_generator)
            r = w.reap()
            self.assertEqual(list(xrange(47)), list(r))

    def test_is_busy(self):
        with Worker() as w:
            w.start_task(sleep, args=(.01,))
            self.assertTrue(w.is_busy)
            sleep(.02)
            self.assertFalse(w.is_busy)

    def test_init_not_busy(self):
        with Worker() as w:
            self.assertFalse(w.is_busy)

    def test_method_call(self):
        obj = _MethodCallTestClass(40)
        with Worker() as w:
            w.start_task(obj.mymethod, args=(7,))
            self.assertEqual(w.reap(), 47)

    def test_method_call_immutable(self):
        obj = _ImmutableTestClass(47)
        with Worker() as w:
            w.start_task(obj.mymethod, args=(42,))
            w.reap()
            self.assertEqual(obj.state, 47)

    def test_result(self):
        with Worker() as w:
            w.start_task(_fourtyseven)
            self.assertEqual(w.reap(), 47)
            w.start_task(_fourtyeight)
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
        with WorkerPool(workers=1) as p:
            p.shutdown()

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

            def shutdown(self):
                pass

        with patch('blockwart.concurrency.Worker', new=MockWorker):
            with WorkerPool(workers=2) as p:
                for i in xrange(2):
                    w = p.get_idle_worker()
                    self.assertEqual(w.busy_counter, 47)
