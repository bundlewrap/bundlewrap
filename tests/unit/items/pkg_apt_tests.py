# -*- coding: utf-8 -*-
from __future__ import unicode_literals
from unittest import TestCase

from mock import MagicMock, patch

from blockwart.exceptions import BundleError
from blockwart.items import pkg_apt
from blockwart.operations import RunResult


class AskTest(TestCase):
    """
    Tests blockwart.items.pkg_apt.AptPkg.ask.
    """
    def test_install(self):
        pkg = pkg_apt.AptPkg(MagicMock(), "foo", {'installed': True})
        status = MagicMock()
        status.info = {'installed': False}
        self.assertEqual(
            pkg.ask(status),
            "status not installed → installed\n",
        )

    def test_remove(self):
        pkg = pkg_apt.AptPkg(MagicMock(), "foo", {'installed': False})
        status = MagicMock()
        status.info = {'installed': True}
        self.assertEqual(
            pkg.ask(status),
            "status installed → not installed\n",
        )


class FixTest(TestCase):
    """
    Tests blockwart.items.pkg_apt.AptPkg.fix.
    """
    def test_install(self):
        node = MagicMock()
        pkg = pkg_apt.AptPkg(node, "foo", {'installed': True})
        pkg.fix(MagicMock())

    def test_remove(self):
        node = MagicMock()
        pkg = pkg_apt.AptPkg(node, "foo", {'installed': False})
        pkg.fix(MagicMock())


class GetStatusTest(TestCase):
    """
    Tests blockwart.items.pkg_apt.AptPkg.get_status.
    """
    @patch('blockwart.items.pkg_apt.pkg_installed')
    def test_installed_ok(self, pkg_installed):
        pkg = pkg_apt.AptPkg(MagicMock(), "foo", {'installed': True})
        pkg_installed.return_value = True
        status = pkg.get_status()
        self.assertTrue(status.correct)

    @patch('blockwart.items.pkg_apt.pkg_installed')
    def test_not_installed_ok(self, pkg_installed):
        pkg = pkg_apt.AptPkg(MagicMock(), "foo", {'installed': False})
        pkg_installed.return_value = False
        status = pkg.get_status()
        self.assertTrue(status.correct)

    @patch('blockwart.items.pkg_apt.pkg_installed')
    def test_installed_not_ok(self, pkg_installed):
        pkg = pkg_apt.AptPkg(MagicMock(), "foo", {'installed': False})
        pkg_installed.return_value = True
        status = pkg.get_status()
        self.assertFalse(status.correct)

    @patch('blockwart.items.pkg_apt.pkg_installed')
    def test_not_installed_not_ok(self, pkg_installed):
        pkg = pkg_apt.AptPkg(MagicMock(), "foo", {'installed': False})
        pkg_installed.return_value = True
        status = pkg.get_status()
        self.assertFalse(status.correct)


class PkgInstalledTest(TestCase):
    """
    Tests blockwart.items.pkg_apt.pkg_installed.
    """
    def test_installed(self):
        runresult = RunResult()
        runresult.return_code = 0
        runresult.stdout = "Status: install ok installed\n"
        node = MagicMock()
        node.run.return_value = runresult
        self.assertTrue(pkg_apt.pkg_installed(node, "foo"))

    def test_not_installed(self):
        runresult = RunResult()
        runresult.return_code = 1
        runresult.stdout = (
            "Package `foo' is not installed and no info is available.\n"
            "Use dpkg --info (= dpkg-deb --info) to examine archive files,\n"
            "and dpkg --contents (= dpkg-deb --contents) to list their contents.\n"
        )
        node = MagicMock()
        node.run.return_value = runresult
        self.assertFalse(pkg_apt.pkg_installed(node, "foo"))


class ValidateAttributesTest(TestCase):
    """
    Tests blockwart.items.pkg_apt.AptPkg.validate_attributes.
    """
    def test_installed_ok(self):
        pkg_apt.AptPkg(MagicMock(), "foo", {'installed': True})
        pkg_apt.AptPkg(MagicMock(), "foo", {'installed': False})

    def test_installed_not_ok(self):
        with self.assertRaises(BundleError):
            pkg_apt.AptPkg(MagicMock(), "foo", {'installed': 0})
        with self.assertRaises(BundleError):
            pkg_apt.AptPkg(MagicMock(), "foo", {'installed': 1})
