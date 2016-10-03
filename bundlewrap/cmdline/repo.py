# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from sys import exit

from ..exceptions import NoSuchPlugin, PluginLocalConflict
from ..plugins import PluginManager
from ..repo import Repository
from ..utils.text import blue, bold, mark_for_translation as _, red
from ..utils.ui import io


def bw_repo_bundle_create(repo, args):
    repo.create_bundle(args['bundle'])


def bw_repo_create(path, args):
    Repository.create(path)


def bw_repo_plugin_install(repo, args):
    pm = PluginManager(repo.path)
    try:
        manifest = pm.install(args['plugin'], force=args['force'])
        io.stdout(_("{x} Installed '{plugin}' (v{version})").format(
            x=blue("i"),
            plugin=args['plugin'],
            version=manifest['version'],
        ))
        if 'help' in manifest:
            io.stdout("")
            for line in manifest['help'].split("\n"):
                io.stdout(line)
    except NoSuchPlugin:
        io.stderr(_("{x} No such plugin: {plugin}").format(x=red("!!!"), plugin=args['plugin']))
        exit(1)
    except PluginLocalConflict as e:
        io.stderr(_("{x} Plugin installation failed: {reason}").format(
            reason=e.message,
            x=red("!!!"),
        ))
        exit(1)


def bw_repo_plugin_list(repo, args):
    pm = PluginManager(repo.path)
    for plugin, version in pm.list():
        io.stdout(_("{plugin} (v{version})").format(plugin=plugin, version=version))


def bw_repo_plugin_remove(repo, args):
    pm = PluginManager(repo.path)
    try:
        pm.remove(args['plugin'], force=args['force'])
    except NoSuchPlugin:
        io.stdout(_("{x} Plugin '{plugin}' is not installed").format(
            x=red("!!!"),
            plugin=args['plugin'],
        ))
        exit(1)


def bw_repo_plugin_search(repo, args):
    pm = PluginManager(repo.path)
    for plugin, desc in pm.search(args['term']):
        io.stdout(_("{plugin}  {desc}").format(desc=desc, plugin=bold(plugin)))


def bw_repo_plugin_update(repo, args):
    pm = PluginManager(repo.path)
    if args['plugin']:
        old_version, new_version = pm.update(
            args['plugin'],
            check_only=args['check_only'],
            force=args['force'],
        )
        if old_version != new_version:
            io.stdout(_("{plugin}  {old_version} → {new_version}").format(
                new_version=new_version,
                old_version=old_version,
                plugin=bold(args['plugin']),
            ))
    else:
        for plugin, version in pm.list():
            old_version, new_version = pm.update(
                plugin,
                check_only=args['check_only'],
                force=args['force'],
            )
            if old_version != new_version:
                io.stdout(_("{plugin}  {old_version} → {new_version}").format(
                    new_version=new_version,
                    old_version=old_version,
                    plugin=bold(plugin),
                ))
