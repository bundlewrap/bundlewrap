# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from unittest import TestCase

from mock import MagicMock, patch

from bundlewrap.cmdline.repo import bw_repo_plugin_install, bw_repo_plugin_list, bw_repo_plugin_search, bw_repo_plugin_update
from bundlewrap.exceptions import NoSuchPlugin


class InstallTest(TestCase):
    @patch('bundlewrap.cmdline.repo.PluginManager.install')
    def test_unknown_plugin(self, install):
        install.side_effect = NoSuchPlugin
        repo = MagicMock()
        repo.path = "/dev/null"
        args = {}
        args['force'] = False
        args['plugin'] = "foo"
        self.assertEqual(
            list(bw_repo_plugin_install(repo, args)),
            ["unknown plugin 'foo'", 1],
        )


class ListTest(TestCase):
    @patch('bundlewrap.cmdline.repo.PluginManager.list')
    def test_list(self, listmethod):
        listmethod.return_value = (("foo", 1),)
        repo = MagicMock()
        repo.path = "/dev/null"
        self.assertEqual(
            list(bw_repo_plugin_list(repo, MagicMock())),
            ["foo (v1)"],
        )


class SearchTest(TestCase):
    @patch('bundlewrap.cmdline.repo.PluginManager.search')
    def test_search(self, search):
        search.return_value = (("foo", "foodesc"),)
        repo = MagicMock()
        repo.path = "/dev/null"
        self.assertEqual(
            list(bw_repo_plugin_search(repo, MagicMock())),
            ["foo: foodesc"],
        )


class UpdateTest(TestCase):
    @patch('bundlewrap.cmdline.repo.PluginManager.update')
    def test_single_update(self, update):
        update.return_value = (1, 2)
        repo = MagicMock()
        repo.path = "/dev/null"
        args = {
            'check_only': False,
            'force': False,
            'plugin': "foo",
        }
        self.assertEqual(
            list(bw_repo_plugin_update(repo, args)),
            ["foo: 1 → 2"],
        )

    @patch('bundlewrap.cmdline.repo.PluginManager.list')
    @patch('bundlewrap.cmdline.repo.PluginManager.update')
    def test_all_update(self, update, listmethod):
        update.return_value = (1, 2)
        listmethod.return_value = (("foo", 1),)
        repo = MagicMock()
        repo.path = "/dev/null"
        args = {
            'check_only': False,
            'force': False,
            'plugin': None,
        }
        self.assertEqual(
            list(bw_repo_plugin_update(repo, args)),
            ["foo: 1 → 2"],
        )
