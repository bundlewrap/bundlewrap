# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from json import dumps, loads
from os import chmod, remove
from os.path import exists, join
from stat import S_IREAD, S_IRGRP, S_IROTH

from requests import get

from .exceptions import NoSuchPlugin, PluginError, PluginLocalConflict
from .utils import download, hash_local_file
from .utils.text import mark_for_translation as _
from .utils.ui import io


BASE_URL = "https://raw.githubusercontent.com/bundlewrap/plugins/master"


class PluginManager(object):
    def __init__(self, path, base_url=BASE_URL):
        self.base_url = base_url
        self.path = path
        if exists(join(self.path, "plugins.json")):
            with open(join(self.path, "plugins.json")) as f:
                self.plugin_db = loads(f.read())
        else:
            self.plugin_db = {}

    @property
    def index(self):
        return get(
            "{}/index.json".format(self.base_url)
        ).json()

    def install(self, plugin, force=False):
        if plugin in self.plugin_db:
            raise PluginError(_("plugin '{plugin}' is already installed").format(plugin=plugin))

        manifest = self.manifest_for_plugin(plugin)

        for file in manifest['provides']:
            target_path = join(self.path, file)
            if exists(target_path) and not force:
                raise PluginLocalConflict(_(
                    "cannot install '{plugin}' because it provides "
                    "'{path}' which already exists"
                ).format(path=target_path, plugin=plugin))

            url = "{}/{}/{}".format(self.base_url, plugin, file)
            download(url, target_path)

            # make file read-only to discourage users from editing them
            # which will block future updates of the plugin
            chmod(target_path, S_IREAD | S_IRGRP | S_IROTH)

        self.record_as_installed(plugin, manifest)

        return manifest

    def list(self):
        for plugin, info in self.plugin_db.items():
            yield (plugin, info['version'])

    def local_modifications(self, plugin):
        try:
            plugin_data = self.plugin_db[plugin]
        except KeyError:
            raise NoSuchPlugin(_(
                "The plugin '{plugin}' is not installed."
            ).format(plugin=plugin))
        local_changes = []
        for filename, checksum in plugin_data['files'].items():
            target_path = join(self.path, filename)
            actual_checksum = hash_local_file(target_path)
            if actual_checksum != checksum:
                local_changes.append((
                    target_path,
                    actual_checksum,
                    checksum,
                ))
        return local_changes

    def manifest_for_plugin(self, plugin):
        r = get(
            "{}/{}/manifest.json".format(self.base_url, plugin)
        )
        if r.status_code == 404:
            raise NoSuchPlugin(plugin)
        else:
            return r.json()

    def record_as_installed(self, plugin, manifest):
        file_hashes = {}

        for file in manifest['provides']:
            target_path = join(self.path, file)
            file_hashes[file] = hash_local_file(target_path)

        self.plugin_db[plugin] = {
            'files': file_hashes,
            'version': manifest['version'],
        }
        self.write_db()

    def remove(self, plugin, force=False):
        if plugin not in self.plugin_db:
            raise NoSuchPlugin(_("plugin '{plugin}' is not installed").format(plugin=plugin))

        for file, db_checksum in self.plugin_db[plugin]['files'].items():
            file_path = join(self.path, file)
            if not exists(file_path):
                continue

            current_checksum = hash_local_file(file_path)
            if db_checksum != current_checksum and not force:
                io.stderr(_(
                    "not removing '{path}' because it has been modified since installation"
                ).format(path=file_path))
                continue

            remove(file_path)

        del self.plugin_db[plugin]
        self.write_db()

    def search(self, term):
        term = term.lower()
        for plugin_name, plugin_data in self.index.items():
            if term in plugin_name.lower() or term in plugin_data['desc'].lower():
                yield (plugin_name, plugin_data['desc'])

    def update(self, plugin, check_only=False, force=False):
        if plugin not in self.plugin_db:
            raise PluginError(_("plugin '{plugin}' is not installed").format(plugin=plugin))

        # before updating anything, we need to check for local modifications
        local_changes = self.local_modifications(plugin)
        if local_changes and not force:
            files = [path for path, c1, c2 in local_changes]
            raise PluginLocalConflict(_(
                "cannot update '{plugin}' because the following files have been modified locally:"
                "\n{files}"
            ).format(files="\n".join(files), plugin=plugin))

        manifest = self.manifest_for_plugin(plugin)

        for file in manifest['provides']:
            file_path = join(self.path, file)
            if exists(file_path) and file not in self.plugin_db[plugin]['files'] and not force:
                # new version added a file that already existed locally
                raise PluginLocalConflict(_(
                    "cannot update '{plugin}' because it would overwrite '{path}'"
                ).format(path=file, plugin=plugin))

        old_version = self.plugin_db[plugin]['version']
        new_version = manifest['version']

        if not check_only and old_version != new_version:
            # actually install files
            for file in manifest['provides']:
                target_path = join(self.path, file)
                url = "{}/{}/{}".format(self.base_url, plugin, file)
                download(url, target_path)

                # make file read-only to discourage users from editing them
                # which will block future updates of the plugin
                chmod(target_path, S_IREAD | S_IRGRP | S_IROTH)

            # check for files that have been removed in the new version
            for file, db_checksum in self.plugin_db[plugin]['files'].items():
                if file not in manifest['provides']:
                    file_path = join(self.path, file)
                    current_checksum = hash_local_file(file_path)
                    if db_checksum != current_checksum and not force:
                        io.stderr(_(
                            "not removing '{path}' because it has been modified since installation"
                        ).format(path=file_path))
                        continue
                    remove(file_path)

            self.record_as_installed(plugin, manifest)

        return (old_version, new_version)

    def write_db(self):
        with open(join(self.path, "plugins.json"), 'w') as f:
            f.write(dumps(self.plugin_db, indent=4, sort_keys=True))
