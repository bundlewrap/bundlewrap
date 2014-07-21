# -*- coding: utf-8 -*-
from __future__ import unicode_literals
from unittest import TestCase

from mock import MagicMock, patch

from bundlewrap.exceptions import BundleError
from bundlewrap.items import svc_systemv
from bundlewrap.operations import RunResult


class AskTest(TestCase):
    """
    Tests bundlewrap.items.svc_systemv.SvcSystemV.ask.
    """
    def test_start(self):
        svc = svc_systemv.SvcSystemV(MagicMock(), "foo", {'running': True})
        status = MagicMock()
        status.info = {'running': False}
        self.assertEqual(
            svc.ask(status),
            "status not running → running\n",
        )

    def test_stop(self):
        svc = svc_systemv.SvcSystemV(MagicMock(), "foo", {'running': False})
        status = MagicMock()
        status.info = {'running': True}
        self.assertEqual(
            svc.ask(status),
            "status running → not running\n",
        )


class FixTest(TestCase):
    """
    Tests bundlewrap.items.svc_systemv.SvcSystemV.fix.
    """
    def test_start(self):
        node = MagicMock()
        svc = svc_systemv.SvcSystemV(node, "foo", {'running': True})
        svc.fix(MagicMock())

    def test_stop(self):
        node = MagicMock()
        svc = svc_systemv.SvcSystemV(node, "foo", {'running': False})
        svc.fix(MagicMock())


class GetStatusTest(TestCase):
    """
    Tests bundlewrap.items.svc_systemv.SvcSystemV.get_status.
    """
    @patch('bundlewrap.items.svc_systemv.svc_running')
    def test_running_ok(self, svc_running):
        svc = svc_systemv.SvcSystemV(MagicMock(), "foo", {'running': True})
        svc_running.return_value = True
        status = svc.get_status()
        self.assertTrue(status.correct)

    @patch('bundlewrap.items.svc_systemv.svc_running')
    def test_not_running_ok(self, svc_running):
        svc = svc_systemv.SvcSystemV(MagicMock(), "foo", {'running': False})
        svc_running.return_value = False
        status = svc.get_status()
        self.assertTrue(status.correct)

    @patch('bundlewrap.items.svc_systemv.svc_running')
    def test_running_not_ok(self, svc_running):
        svc = svc_systemv.SvcSystemV(MagicMock(), "foo", {'running': False})
        svc_running.return_value = True
        status = svc.get_status()
        self.assertFalse(status.correct)

    @patch('bundlewrap.items.svc_systemv.svc_running')
    def test_not_running_not_ok(self, svc_running):
        svc = svc_systemv.SvcSystemV(MagicMock(), "foo", {'running': False})
        svc_running.return_value = True
        status = svc.get_status()
        self.assertFalse(status.correct)


class svcrunningTest(TestCase):
    """
    Tests bundlewrap.items.svc_systemv.svc_running.
    """
    def test_running(self):
        runresult = RunResult()
        runresult.return_code = 0
        runresult.stdout = "whatever, does not matter"
        node = MagicMock()
        node.run.return_value = runresult
        self.assertTrue(svc_systemv.svc_running(node, "foo"))

    def test_not_running(self):
        runresult = RunResult()
        runresult.return_code = 3
        runresult.stdout = "whatever, does not matter"
        node = MagicMock()
        node.run.return_value = runresult
        self.assertFalse(svc_systemv.svc_running(node, "foo"))


class ValidateAttributesTest(TestCase):
    """
    Tests bundlewrap.items.svc_systemv.SvcSystemV.validate_attributes.
    """
    def test_running_ok(self):
        svc_systemv.SvcSystemV(MagicMock(), "foo", {'running': True})
        svc_systemv.SvcSystemV(MagicMock(), "foo", {'running': False})

    def test_running_not_ok(self):
        with self.assertRaises(BundleError):
            svc_systemv.SvcSystemV(MagicMock(), "foo", {'running': 0})
        with self.assertRaises(BundleError):
            svc_systemv.SvcSystemV(MagicMock(), "foo", {'running': 1})
