# -*- coding: utf-8 -*-
from __future__ import unicode_literals
from collections import defaultdict
from os.path import normpath
from pipes import quote

from bundlewrap.exceptions import BundleError
from bundlewrap.items import Item, ItemStatus
from bundlewrap.utils import LOG
from bundlewrap.utils.remote import PathInfo
from bundlewrap.utils.text import mark_for_translation as _
from bundlewrap.utils.text import bold, is_subdirectory


def validator_mode(item_id, value):
    value = str(value)
    if not value.isdigit():
        raise BundleError(
            _("mode for {item} should be written as digits, got: '{value}'"
              "").format(item=item_id, value=value)
        )
    for digit in value:
        if int(digit) > 7 or int(digit) < 0:
            raise BundleError(_(
                "invalid mode for {item}: '{value}'"
            ).format(item=item_id, value=value))
    if not len(value) == 3 and not len(value) == 4:
        raise BundleError(_(
            "mode for {item} should be three or four digits long, was: '{value}'"
        ).format(item=item_id, value=value))

ATTRIBUTE_VALIDATORS = defaultdict(lambda: lambda id, value: None)
ATTRIBUTE_VALIDATORS.update({
    'mode': validator_mode,
})


class Directory(Item):
    """
    A directory.
    """
    BUNDLE_ATTRIBUTE_NAME = "directories"
    ITEM_ATTRIBUTES = {
        'group': None,
        'mode': None,
        'owner': None,
    }
    ITEM_TYPE_NAME = "directory"
    NEEDS_STATIC = ["user:"]

    def __repr__(self):
        return "<Directory path:{}>".format(
            quote(self.name),
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

        for fix_type in ('mode', 'owner', 'group'):
            if fix_type in status.info['needs_fixing']:
                if fix_type == 'group' and \
                        'owner' in status.info['needs_fixing']:
                    # owner and group are fixed with a single chown
                    continue
                LOG.info(_("{node}:{bundle}:{item}: fixing {fix_type}...").format(
                    bundle=self.bundle.name,
                    item=self.id,
                    fix_type=fix_type,
                    node=self.node.name,
                ))
                getattr(self, "_fix_" + fix_type)(status)

    def _fix_mode(self, status):
        self.node.run("chmod {} -- {}".format(
            self.attributes['mode'],
            quote(self.name),
        ))

    def _fix_owner(self, status):
        group = self.attributes['group'] or ""
        if group:
            group = ":" + quote(group)
        self.node.run("chown {}{} -- {}".format(
            quote(self.attributes['owner'] or ""),
            group,
            quote(self.name),
        ))
    _fix_group = _fix_owner

    def _fix_type(self, status):
        self.node.run("rm -rf -- {}".format(quote(self.name)))
        self.node.run("mkdir -p -- {}".format(quote(self.name)))
        if self.attributes['mode']:
            self._fix_mode(status)
        if self.attributes['owner'] or self.attributes['group']:
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
                    item.ITEM_TYPE_NAME in ("file", "symlink") and
                    item.name == self.name
                )
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

        if not path_info.is_directory:
            status_info['needs_fixing'].append('type')
        else:
            if self.attributes['mode'] is not None and \
                    path_info.mode != self.attributes['mode']:
                status_info['needs_fixing'].append('mode')
            if self.attributes['owner'] is not None and \
                    path_info.owner != self.attributes['owner']:
                status_info['needs_fixing'].append('owner')
            if self.attributes['group'] is not None and \
                    path_info.group != self.attributes['group']:
                status_info['needs_fixing'].append('group')

        if status_info['needs_fixing']:
            correct = False
        return ItemStatus(correct=correct, info=status_info)

    def patch_attributes(self, attributes):
        if 'mode' in attributes and attributes['mode'] is not None:
            attributes['mode'] = str(attributes['mode']).zfill(4)
        return attributes

    @classmethod
    def validate_attributes(cls, bundle, item_id, attributes):
        for key, value in attributes.items():
            ATTRIBUTE_VALIDATORS[key](item_id, value)

    @classmethod
    def validate_name(cls, bundle, name):
        if normpath(name) != name:
            raise BundleError(_(
                "'{path}' is an invalid directory path, "
                "should be '{normpath}' (bundle '{bundle}')"
            ).format(
                bundle=bundle.name,
                normpath=normpath(name),
                path=name,
            ))
