# -*- coding: utf-8 -*-
from __future__ import unicode_literals
from collections import defaultdict
from os.path import normpath
from pipes import quote

from blockwart.exceptions import BundleError
from blockwart.items import Item, ItemStatus
from blockwart.utils import LOG
from blockwart.utils.remote import PathInfo
from blockwart.utils.text import mark_for_translation as _
from blockwart.utils.text import bold, is_subdirectory


def validator_mode(item_id, value):
    if not value.isdigit():
        raise BundleError(
            _("mode for {} should be written as digits, got: '{}'"
              "").format(item_id, value)
        )
    for digit in value:
        if int(digit) > 7 or int(digit) < 0:
            raise BundleError(
                _("invalid mode for {}: '{}'").format(item_id, value),
            )
    if not len(value) == 3 and not len(value) == 4:
        raise BundleError(
            _("mode for {} should be three or four digits long, was: '{}'"
              "").format(item_id, value)
        )

ATTRIBUTE_VALIDATORS = defaultdict(lambda: lambda id, value: None)
ATTRIBUTE_VALIDATORS.update({
    'mode': validator_mode,
})


class Directory(Item):
    """
    A directory.
    """
    BUNDLE_ATTRIBUTE_NAME = "directories"
    DEPENDS_STATIC = ["user:"]
    ITEM_ATTRIBUTES = {
        'group': "root",
        'mode': "0775",
        'owner': "root",
    }
    ITEM_TYPE_NAME = "directory"

    def __repr__(self):
        return "<Directory path:{} owner:{} group:{} mode:{}>".format(
            quote(self.name),
            self.attributes['owner'],
            self.attributes['group'],
            self.attributes['mode'],
        )

    def ask(self, status):
        if 'type' in status.info['needs_fixing']:
            if not status.info['path_info'].exists:
                return _("Doesn't exist. Do you want to create it?")
            else:
                return _(
                    "Not a directory. "
                    "The `file` utility says it's a '{}'.\n"
                    "Do you want it removed and replaced?"
                ).format(
                    status.info['path_info'].desc,
                )

        question = ""

        if 'mode' in status.info['needs_fixing']:
            question += "{} {} → {}\n".format(
                bold(_("mode")),
                status.info['path_info'].mode,
                self.attributes['mode'],
            )

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
            LOG.info(_("{}:{}: fixing type...").format(
                self.node.name,
                self.id,
            ))
            self._fix_type(status)
            return

        for fix_type in ('mode', 'owner', 'group'):
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

    def _fix_mode(self, status):
        self.node.run("chmod {} {}".format(
            self.attributes['mode'],
            quote(self.name),
        ))

    def _fix_owner(self, status):
        self.node.run("chown {}:{} {}".format(
            quote(self.attributes['owner']),
            quote(self.attributes['group']),
            quote(self.name),
        ))
    _fix_group = _fix_owner

    def _fix_type(self, status):
        self.node.run("rm -rf {}".format(quote(self.name)))
        self.node.run("mkdir -p {}".format(quote(self.name)))
        self._fix_mode(status)
        self._fix_owner(status)

    def get_auto_deps(self, items):
        deps = []
        for item in items:
            if item == self:
                continue
            if (
                (
                    item.ITEM_TYPE_NAME == "file" and
                    is_subdirectory(item.name, self.name)
                )
                or
                (
                    item.ITEM_TYPE_NAME in ("directory", "file", "symlink") and
                    item.name == self.name
                )
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

        if not path_info.is_directory:
            status_info['needs_fixing'].append('type')
        else:
            if path_info.mode != self.attributes['mode']:
                status_info['needs_fixing'].append('mode')
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
                "'{}' is an invalid directory path, should be '{}' (bundle '{}')"
            ).format(
                name,
                normpath(name),
                bundle.name,
            ))
