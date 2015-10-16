# -*- coding: utf-8 -*-
from __future__ import unicode_literals
from unittest import TestCase

try:
    from unittest.mock import MagicMock, patch
except ImportError:
    from mock import MagicMock, patch

from bundlewrap.exceptions import BundleError
from bundlewrap.items import pkg_pip
from bundlewrap.operations import RunResult


class AskTest(TestCase):
    """
    Tests bundlewrap.items.pkg_pip.PipPkg.ask.
    """
    def test_install(self):
        pkg = pkg_pip.PipPkg(MagicMock(), "foo", {'installed': True})
        status = MagicMock()
        status.info = {'installed': False, 'version': None}
        self.assertEqual(
            pkg.ask(status),
            "status not installed → installed\n",
        )

    def test_remove(self):
        pkg = pkg_pip.PipPkg(MagicMock(), "foo", {'installed': False})
        status = MagicMock()
        status.info = {'installed': True, 'version': "1.0"}
        self.assertEqual(
            pkg.ask(status),
            "status 1.0 → not installed\n",
        )


class FixTest(TestCase):
    """
    Tests bundlewrap.items.pkg_pip.PipPkg.fix.
    """
    def test_install(self):
        node = MagicMock()
        pkg = pkg_pip.PipPkg(node, "foo", {'installed': True})
        pkg.fix(MagicMock())

    def test_install_version(self):
        node = MagicMock()
        pkg = pkg_pip.PipPkg(node, "foo", {'installed': True, 'version': "1.0"})
        pkg.fix(MagicMock())

    def test_remove(self):
        node = MagicMock()
        pkg = pkg_pip.PipPkg(node, "foo", {'installed': False})
        pkg.fix(MagicMock())


class GetStatusTest(TestCase):
    """
    Tests bundlewrap.items.pkg_pip.PipPkg.get_status.
    """
    @patch('bundlewrap.items.pkg_pip.pkg_installed')
    def test_installed_ok(self, pkg_installed):
        pkg = pkg_pip.PipPkg(MagicMock(), "foo", {'installed': True})
        pkg_installed.return_value = "1.0"
        status = pkg.get_status()
        self.assertTrue(status.correct)
        self.assertEqual(status.info['version'], "1.0")

    @patch('bundlewrap.items.pkg_pip.pkg_installed')
    def test_not_installed_ok(self, pkg_installed):
        pkg = pkg_pip.PipPkg(MagicMock(), "foo", {'installed': False})
        pkg_installed.return_value = False
        status = pkg.get_status()
        self.assertTrue(status.correct)

    @patch('bundlewrap.items.pkg_pip.pkg_installed')
    def test_installed_not_ok(self, pkg_installed):
        pkg = pkg_pip.PipPkg(MagicMock(), "foo", {'installed': False})
        pkg_installed.return_value = "1.0"
        status = pkg.get_status()
        self.assertFalse(status.correct)

    @patch('bundlewrap.items.pkg_pip.pkg_installed')
    def test_not_installed_not_ok(self, pkg_installed):
        pkg = pkg_pip.PipPkg(MagicMock(), "foo", {'installed': False})
        pkg_installed.return_value = True
        status = pkg.get_status()
        self.assertFalse(status.correct)

    @patch('bundlewrap.items.pkg_pip.pkg_installed')
    def test_version_not_ok(self, pkg_installed):
        pkg = pkg_pip.PipPkg(MagicMock(), "foo", {
            'installed': True,
            'version': "2.0",
        })
        pkg_installed.return_value = "1.0"
        status = pkg.get_status()
        self.assertFalse(status.correct)


class PkgInstalledTest(TestCase):
    """
    Tests bundlewrap.items.pkg_pip.pkg_installed.
    """
    def test_installed(self):
        runresult = RunResult()
        runresult.return_code = 0
        runresult.stdout = "Status: install ok installed\n"
        node = MagicMock()
        node.run.return_value = runresult
        self.assertTrue(pkg_pip.pkg_installed(node, "foo"))

    def test_not_installed(self):
        runresult = RunResult()
        runresult.return_code = 1
        runresult.stdout = "Error: No matching Packages to list\n"
        node = MagicMock()
        node.run.return_value = runresult
        self.assertFalse(pkg_pip.pkg_installed(node, "foo"))


class ValidateAttributesTest(TestCase):
    """
    Tests bundlewrap.items.pkg_pip.PipPkg.validate_attributes.
    """
    def test_installed_ok(self):
        pkg_pip.PipPkg(MagicMock(), "foo", {'installed': True})
        pkg_pip.PipPkg(MagicMock(), "foo", {'installed': True, 'version': "1.0"})
        pkg_pip.PipPkg(MagicMock(), "foo", {'installed': False})

    def test_installed_not_ok(self):
        with self.assertRaises(BundleError):
            pkg_pip.PipPkg(MagicMock(), "foo", {'installed': 0})
        with self.assertRaises(BundleError):
            pkg_pip.PipPkg(MagicMock(), "foo", {'installed': 1})
        with self.assertRaises(BundleError):
            pkg_pip.PipPkg(MagicMock(), "foo", {'installed': False, 'version': "1.0"})
