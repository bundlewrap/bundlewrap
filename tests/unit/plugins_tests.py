from json import dumps, loads
from os.path import exists, join
from shutil import rmtree
from tempfile import mkdtemp
from unittest import TestCase

from mock import MagicMock, patch

from bundlewrap import plugins
from bundlewrap.exceptions import NoSuchPlugin, PluginLocalConflict


class TmpDirTest(TestCase):
    def setUp(self):
        self.tmpdir = mkdtemp()

    def tearDown(self):
        rmtree(self.tmpdir)


class ListTest(TmpDirTest):
    def test_list_plugin(self):
        with open(join(self.tmpdir, "plugins.json"), 'w') as f:
            f.write(dumps({
                "plugin1": {
                    "files": {
                        "file1": "12345",
                        "file2": "67890",
                    },
                    "version": 1,
                },
            }))

        pm = plugins.PluginManager(self.tmpdir)
        self.assertEqual(list(pm.list()), [("plugin1", 1)])


class RemoveTest(TmpDirTest):
    def test_remove_plugin(self):
        with open(join(self.tmpdir, "plugins.json"), 'w') as f:
            f.write(dumps({
                "plugin1": {
                    "files": {
                        "file1": "356a192b7913b04c54574d18c28d46e6395428ab",
                    },
                    "version": 1,
                },
            }))

        with open(join(self.tmpdir, "file1"), 'w') as f:
            f.write("1")

        pm = plugins.PluginManager(self.tmpdir)

        with self.assertRaises(NoSuchPlugin):
            pm.remove("plugin2")

        self.assertTrue(exists(join(self.tmpdir, "file1")))
        pm.remove("plugin1")
        self.assertFalse(exists(join(self.tmpdir, "file1")))


        with open(join(self.tmpdir, "plugins.json")) as f:
            plugin_db = f.read()
        self.assertEqual(
            loads(plugin_db),
            {},
        )


    def test_leave_modified(self):
        with open(join(self.tmpdir, "plugins.json"), 'w') as f:
            f.write(dumps({
                "plugin1": {
                    "files": {
                        "file1": "different_hash",
                        "404": "",
                    },
                    "version": 1,
                },
            }))

        with open(join(self.tmpdir, "file1"), 'w') as f:
            f.write("1")

        pm = plugins.PluginManager(self.tmpdir)

        self.assertTrue(exists(join(self.tmpdir, "file1")))
        pm.remove("plugin1")
        self.assertTrue(exists(join(self.tmpdir, "file1")))

        with open(join(self.tmpdir, "plugins.json")) as f:
            plugin_db = f.read()
        self.assertEqual(
            loads(plugin_db),
            {},
        )


class SearchTest(TmpDirTest):
    @patch('bundlewrap.plugins.get')
    def test_search_empty(self, get):
        getresult = MagicMock()
        getresult.json.return_value = {}
        get.return_value = getresult

        pm = plugins.PluginManager(self.tmpdir)

        self.assertEqual(
            list(pm.search("foo")),
            [],
        )

    @patch('bundlewrap.plugins.get')
    def test_search_404(self, get):
        getresult = MagicMock()
        getresult.json.return_value = {
            'barplugin': {
                'desc': "Description",
            },
        }
        get.return_value = getresult

        pm = plugins.PluginManager(self.tmpdir)

        self.assertEqual(
            list(pm.search("foo")),
            [],
        )

    @patch('bundlewrap.plugins.get')
    def test_search_name(self, get):
        getresult = MagicMock()
        getresult.json.return_value = {
            'barplugin': {
                'desc': "Description",
            },
        }
        get.return_value = getresult

        pm = plugins.PluginManager(self.tmpdir)

        self.assertEqual(
            list(pm.search("bar")),
            [("barplugin", "Description")],
        )

    @patch('bundlewrap.plugins.get')
    def test_search_desc(self, get):
        getresult = MagicMock()
        getresult.json.return_value = {
            'barplugin': {
                'desc': "Description",
            },
        }
        get.return_value = getresult

        pm = plugins.PluginManager(self.tmpdir)

        self.assertEqual(
            list(pm.search("escript")),
            [("barplugin", "Description")],
        )


class InstallTest(TmpDirTest):
    @patch('bundlewrap.plugins.download')
    @patch('bundlewrap.plugins.get')
    def test_install(self, get, download):
        getresult = MagicMock()
        getresult.json.return_value = {
            'provides': [
                'file1',
            ],
            'version': 1,
        }
        get.return_value = getresult

        def write_file(*args, **kwargs):
            with open(join(self.tmpdir, "file1"), 'w') as f:
                f.write("remote content")
        download.side_effect = write_file

        pm = plugins.PluginManager(self.tmpdir)
        pm.install("plugin")

        download.assert_called_once_with(
            plugins.BASE_URL + '/plugin/file1',
            join(self.tmpdir, "file1"),
        )

        with open(join(self.tmpdir, "plugins.json")) as f:
            plugin_db = f.read()
        self.assertEqual(
            loads(plugin_db),
            {
                'plugin': {
                    'files': {
                        'file1': '657290b41bea0e18a57aea274520fd07f87fdb5f',
                    },
                    'version': 1,
                },
            },
        )

class InstallNoForceConflictTest(TmpDirTest):
    @patch('bundlewrap.plugins.get')
    def test_no_force_conflict(self, get):
        getresult = MagicMock()
        getresult.json.return_value = {
            'provides': [
                'file1',
            ],
            'version': 1,
        }
        get.return_value = getresult

        with open(join(self.tmpdir, "file1"), 'w') as f:
            f.write("local content")

        pm = plugins.PluginManager(self.tmpdir)
        with self.assertRaises(PluginLocalConflict):
            pm.install("plugin")


class InstallForceConflictTest(TmpDirTest):
    @patch('bundlewrap.plugins.download')
    @patch('bundlewrap.plugins.get')
    def test_force_conflict(self, get, download):
        getresult = MagicMock()
        getresult.json.return_value = {
            'provides': [
                'file1',
            ],
            'version': 1,
        }
        get.return_value = getresult

        def write_file(*args, **kwargs):
            with open(join(self.tmpdir, "file1"), 'w') as f:
                f.write("remote content")
        download.side_effect = write_file

        with open(join(self.tmpdir, "file1"), 'w') as f:
            f.write("local content")

        pm = plugins.PluginManager(self.tmpdir)
        pm.install("plugin", force=True)

        download.assert_called_once_with(
            plugins.BASE_URL + '/plugin/file1',
            join(self.tmpdir, "file1"),
        )

        with open(join(self.tmpdir, "plugins.json")) as f:
            plugin_db = f.read()
        self.assertEqual(
            loads(plugin_db),
            {
                'plugin': {
                    'files': {
                        'file1': '657290b41bea0e18a57aea274520fd07f87fdb5f',
                    },
                    'version': 1,
                },
            },
        )


class UpdateTest(TmpDirTest):
    @patch('bundlewrap.plugins.download')
    @patch('bundlewrap.plugins.get')
    def test_update(self, get, download):
        with open(join(self.tmpdir, "plugins.json"), 'w') as f:
            f.write(dumps({
                "plugin": {
                    "files": {
                        "file1": "621971d8347db54e476db2660e15753c1b84d33b",
                        "file2": "621971d8347db54e476db2660e15753c1b84d33b",
                    },
                    "version": 1,
                },
            }))

        getresult = MagicMock()
        getresult.json.return_value = {
            'provides': [
                'file1',
            ],
            'version': 2,
        }
        get.return_value = getresult

        def write_file(*args, **kwargs):
            with open(join(self.tmpdir, "file1"), 'w') as f:
                f.write("remote content")
        download.side_effect = write_file

        with open(join(self.tmpdir, "file1"), 'w') as f:
            f.write("old content")
        with open(join(self.tmpdir, "file2"), 'w') as f:
            f.write("old content")

        pm = plugins.PluginManager(self.tmpdir)
        pm.update("plugin")

        download.assert_called_once_with(
            plugins.BASE_URL + '/plugin/file1',
            join(self.tmpdir, "file1"),
        )

        with open(join(self.tmpdir, "plugins.json")) as f:
            plugin_db = f.read()
        self.assertEqual(
            loads(plugin_db),
            {
                'plugin': {
                    'files': {
                        'file1': '657290b41bea0e18a57aea274520fd07f87fdb5f',
                    },
                    'version': 2,
                },
            },
        )
        self.assertFalse(exists(join(self.tmpdir, "file2")))


class UpdateConflictTest(TmpDirTest):
    @patch('bundlewrap.plugins.download')
    @patch('bundlewrap.plugins.get')
    def test_update_conflict(self, get, download):
        with open(join(self.tmpdir, "plugins.json"), 'w') as f:
            f.write(dumps({
                "plugin": {
                    "files": {
                        "file1": "621971d8347db54e476db2660e15753c1b84d33b",
                    },
                    "version": 1,
                },
            }))

        getresult = MagicMock()
        getresult.json.return_value = {
            'provides': [
                'file1',
            ],
            'version': 2,
        }
        get.return_value = getresult

        def write_file(*args, **kwargs):
            with open(join(self.tmpdir, "file1"), 'w') as f:
                f.write("remote content")
        download.side_effect = write_file

        with open(join(self.tmpdir, "file1"), 'w') as f:
            f.write("local content")

        pm = plugins.PluginManager(self.tmpdir)
        with self.assertRaises(PluginLocalConflict):
            pm.update("plugin")
