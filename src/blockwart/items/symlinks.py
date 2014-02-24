# -*- coding: utf-8 -*-
from __future__ import unicode_literals
from collections import defaultdict
from os.path import dirname, normpath
from pipes import quote

from blockwart.exceptions import BundleError
from blockwart.items import Item, ItemStatus
from blockwart.utils import LOG
from blockwart.utils.remote import PathInfo
from blockwart.utils.text import mark_for_translation as _
from blockwart.utils.text import bold, is_subdirectory


ATTRIBUTE_VALIDATORS = defaultdict(lambda: lambda id, value: None)


class Symlink(Item):
    """
    A symbolic link.
    """
    BUNDLE_ATTRIBUTE_NAME = "symlinks"
    DEPENDS_STATIC = ["user:"]
    ITEM_ATTRIBUTES = {
        'group': "root",
        'owner': "root",
        'target': None,
    }
    ITEM_TYPE_NAME = "symlink"
    REQUIRED_ATTRIBUTES = ['target']

    def __repr__(self):
        return "<Symlink path:{} target:{} owner:{} group:{}>".format(
            quote(self.name),
            self.attributes['target'],
            self.attributes['owner'],
            self.attributes['group'],
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

        return question.rstrip("\n")

    def fix(self, status):
        if 'type' in status.info['needs_fixing']:
            # fixing the type fixes everything
            if status.info['path_info'].exists:
                LOG.info(_("{}:{}: fixing type...").format(self.node.name, self.id))
            else:
                LOG.info(_("{}:{}: creating...").format(self.node.name, self.id))
            self._fix_type(status)
            return

        for fix_type in ('owner', 'group'):
            if fix_type in status.info['needs_fixing']:
                if fix_type == 'group' and \
                        'owner' in status.info['needs_fixing']:
                    # owner and group are fixed with a single chown
                    continue
                LOG.info(_("{}:{}: fixing {}...").format(
                    self.node.name,
                    self.id,
                    fix_type,
                ))
                getattr(self, "_fix_" + fix_type)(status)

    def _fix_owner(self, status):
        self.node.run("chown -h {}:{} {}".format(
            quote(self.attributes['owner']),
            quote(self.attributes['group']),
            quote(self.name),
        ))
    _fix_group = _fix_owner

    def _fix_type(self, status):
        self.node.run("rm -rf {}".format(quote(self.name)))
        self.node.run("mkdir -p {}".format(quote(dirname(self.name))))
        self.node.run("ln -s {} {}".format(quote(self.attributes['target']),
                                           quote(self.name)))
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
                    "{} (from bundle '{}') blocking path to "
                    "{} (from bundle '{}')"
                ).format(
                    item.id,
                    item.bundle.name,
                    self.id,
                    self.bundle.name,
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
            if path_info.owner != self.attributes['owner']:
                status_info['needs_fixing'].append('owner')
            if path_info.group != self.attributes['group']:
                status_info['needs_fixing'].append('group')

        if status_info['needs_fixing']:
            correct = False
        return ItemStatus(correct=correct, info=status_info)

    def validate_attributes(self, attributes):
        for key, value in attributes.items():
            ATTRIBUTE_VALIDATORS[key](self.id, value)

    @classmethod
    def validate_name(cls, bundle, name):
        if normpath(name) != name:
            raise BundleError(_(
                "'{}' is an invalid symlink path, should be '{}' (bundle '{}')"
            ).format(
                name,
                normpath(name),
                bundle.name,
            ))
