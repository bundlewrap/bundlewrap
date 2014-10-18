# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from ..exceptions import NoSuchPlugin, PluginLocalConflict
from ..plugins import PluginManager
from ..repo import Repository
from ..utils.text import mark_for_translation as _, red


def bw_repo_bundle_create(repo, args):
    repo.create_bundle(args['bundle'])


def bw_repo_create(path, args):
    Repository.create(path)


def bw_repo_plugin_install(repo, args):
    pm = PluginManager(repo.path)
    try:
        manifest = pm.install(args['plugin'], force=args['force'])
        yield _("installed '{plugin}' (v{version})").format(
            plugin=args['plugin'],
            version=manifest['version'],
        )
        if 'help' in manifest:
            yield ""
            for line in manifest['help'].split("\n"):
                yield line
    except NoSuchPlugin:
        yield _("unknown plugin '{plugin}'").format(plugin=args['plugin'])
        yield 1
    except PluginLocalConflict as e:
        yield _("{x} plugin installation failed: {reason}").format(
            reason=e.message,
            x=red("!!!"),
        )
        yield 1


def bw_repo_plugin_list(repo, args):
    pm = PluginManager(repo.path)
    for plugin, version in pm.list():
        yield _("{plugin} (v{version})").format(plugin=plugin, version=version)


def bw_repo_plugin_remove(repo, args):
    pm = PluginManager(repo.path)
    try:
        pm.remove(args['plugin'], force=args['force'])
    except NoSuchPlugin:
        yield _("plugin '{plugin}' is not installed").format(plugin=args['plugin'])
        yield 1


def bw_repo_plugin_search(repo, args):
    pm = PluginManager(repo.path)
    for plugin, desc in pm.search(args['term']):
        yield _("{plugin}: {desc}").format(desc=desc, plugin=plugin)


def bw_repo_plugin_update(repo, args):
    pm = PluginManager(repo.path)
    if args['plugin']:
        old_version, new_version = pm.update(
            args['plugin'],
            check_only=args['check_only'],
            force=args['force'],
        )
        if old_version != new_version:
            yield _("{plugin}: {old_version} → {new_version}").format(
                new_version=new_version,
                old_version=old_version,
                plugin=args['plugin'],
            )
    else:
        for plugin, version in pm.list():
            old_version, new_version = pm.update(
                plugin,
                check_only=args['check_only'],
                force=args['force'],
            )
            if old_version != new_version:
                yield _("{plugin}: {old_version} → {new_version}").format(
                    new_version=new_version,
                    old_version=old_version,
                    plugin=plugin,
                )
