# -*- coding: utf-8 -*-
from __future__ import unicode_literals
from collections import defaultdict
from os.path import dirname, normpath
from pipes import quote

from bundlewrap.exceptions import BundleError
from bundlewrap.items import Item, ItemStatus
from bundlewrap.utils import LOG
from bundlewrap.utils.remote import PathInfo
from bundlewrap.utils.text import mark_for_translation as _
from bundlewrap.utils.text import bold, is_subdirectory


ATTRIBUTE_VALIDATORS = defaultdict(lambda: lambda id, value: None)


class Symlink(Item):
    """
    A symbolic link.
    """
    BUNDLE_ATTRIBUTE_NAME = "symlinks"
    ITEM_ATTRIBUTES = {
        'group': None,
        'owner': None,
        'target': None,
    }
    ITEM_TYPE_NAME = "symlink"
    REQUIRED_ATTRIBUTES = ['target']
    NEEDS_STATIC = ["user:"]

    def __repr__(self):
        return "<Symlink path:{} target:{}>".format(
            quote(self.name),
            self.attributes['target'],
        )

    def ask(self, status):
        if 'type' in status.info['needs_fixing']:
            if not status.info['path_info'].exists:
                return _("Doesn't exist.")
            else:
                return "{} {} → {}\n".format(
                    bold(_("type")),
                    status.info['path_info'].desc,
                    _("file"),
                )

        question = ""

        if 'owner' in status.info['needs_fixing']:
            question += "{} {} → {}\n".format(
                bold(_("owner")),
                status.info['path_info'].owner,
                self.attributes['owner'],
            )

        if 'group' in status.info['needs_fixing']:
            question += "{} {} → {}\n".format(
                bold(_("group")),
                status.info['path_info'].group,
                self.attributes['group'],
            )

        if 'target' in status.info['needs_fixing']:
            question += "{} {}\n".format(
                bold(_("target")),
                status.info['path_info'].symlink_target,
            )
            question += "{}{} {}\n".format(
                " " * (len(_("target")) - 1),
                bold("→"),
                self.attributes['target'],
            )

        return question.rstrip("\n")

    def fix(self, status):
        if 'type' in status.info['needs_fixing']:
            # fixing the type fixes everything
            if status.info['path_info'].exists:
                LOG.info(_("{node}:{bundle}:{item}: fixing type...").format(
                    bundle=self.bundle.name,
                    item=self.id,
                    node=self.node.name,
                ))
            else:
                LOG.info(_("{node}:{bundle}:{item}: creating...").format(
                    bundle=self.bundle.name,
                    item=self.id,
                    node=self.node.name,
                ))
            self._fix_type(status)
            return

        for fix_type in ('owner', 'group', 'target'):
            if fix_type in status.info['needs_fixing']:
                if fix_type == 'group' and \
                        'owner' in status.info['needs_fixing']:
                    # owner and group are fixed with a single chown
                    continue
                LOG.info(_("{node}:{item}: fixing {type}...").format(
                    item=self.id,
                    node=self.node.name,
                    type=fix_type,
                ))
                getattr(self, "_fix_" + fix_type)(status)

    def _fix_owner(self, status):
        group = self.attributes['group'] or ""
        if group:
            group = ":" + quote(group)
        self.node.run("chown -h {}{} -- {}".format(
            quote(self.attributes['owner'] or ""),
            group,
            quote(self.name),
        ))
    _fix_group = _fix_owner

    def _fix_target(self, status):
        self.node.run("ln -sf -- {} {}".format(
            quote(self.attributes['target']),
            quote(self.name),
        ))

    def _fix_type(self, status):
        self.node.run("rm -rf -- {}".format(quote(self.name)))
        self.node.run("mkdir -p -- {}".format(quote(dirname(self.name))))
        self.node.run("ln -s -- {} {}".format(
            quote(self.attributes['target']),
            quote(self.name),
        ))
        if self.attributes['owner'] or self.attributes['group']:
            self._fix_owner(status)

    def get_auto_deps(self, items):
        deps = []
        for item in items:
            if item == self:
                continue
            if item.ITEM_TYPE_NAME == "file" and (
                is_subdirectory(item.name, self.name) or
                item.name == self.name
            ):
                raise BundleError(_(
                    "{item1} (from bundle '{bundle1}') blocking path to "
                    "{item2} (from bundle '{bundle2}')"
                ).format(
                    item1=item.id,
                    bundle1=item.bundle.name,
                    item2=self.id,
                    bundle2=self.bundle.name,
                ))
            elif item.ITEM_TYPE_NAME in ("directory", "symlink"):
                if is_subdirectory(item.name, self.name):
                    deps.append(item.id)
        return deps

    def get_status(self):
        correct = True
        path_info = PathInfo(self.node, self.name)
        status_info = {'needs_fixing': [], 'path_info': path_info}

        if not path_info.is_symlink:
            status_info['needs_fixing'].append('type')
        else:
            if path_info.symlink_target != self.attributes['target']:
                status_info['needs_fixing'].append('target')
            if self.attributes['owner'] is not None and \
                    path_info.owner != self.attributes['owner']:
                status_info['needs_fixing'].append('owner')
            if self.attributes['group'] is not None and \
                    path_info.group != self.attributes['group']:
                status_info['needs_fixing'].append('group')

        if status_info['needs_fixing']:
            correct = False
        return ItemStatus(correct=correct, info=status_info)

    @classmethod
    def validate_attributes(cls, bundle, item_id, attributes):
        for key, value in attributes.items():
            ATTRIBUTE_VALIDATORS[key](item_id, value)

    @classmethod
    def validate_name(cls, bundle, name):
        if normpath(name) == "/":
            raise BundleError(_("'/' cannot be a file"))
        if normpath(name) != name:
            raise BundleError(_(
                "'{path}' is an invalid symlink path, should be '{normpath}' (bundle '{bundle}')"
            ).format(
                path=name,
                normpath=normpath(name),
                bundle=bundle.name,
            ))
