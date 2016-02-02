# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from collections import defaultdict
from os.path import dirname, normpath
from pipes import quote

from bundlewrap.exceptions import BundleError
from bundlewrap.items import Item
from bundlewrap.utils.remote import PathInfo
from bundlewrap.utils.text import mark_for_translation as _
from bundlewrap.utils.text import is_subdirectory


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

    def __repr__(self):
        return "<Symlink path:{} target:{}>".format(
            quote(self.name),
            self.attributes['target'],
        )

    def cdict(self):
        cdict = {
            'target': self.attributes['target'],
            'type': 'symlink',
        }
        for optional_attr in ('group', 'owner'):
            if self.attributes[optional_attr] is not None:
                cdict[optional_attr] = self.attributes[optional_attr]
        return cdict

    def fix(self, status):
        if status.must_be_created or 'type' in status.keys_to_fix:
            # fixing the type fixes everything
            self._fix_type(status)
            return

        for fix_type in ('owner', 'group', 'target'):
            if fix_type in status.keys_to_fix:
                if fix_type == 'group' and 'owner' in status.keys_to_fix:
                    # owner and group are fixed with a single chown
                    continue
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
            elif item.ITEM_TYPE_NAME == "user" and item.name == self.attributes['owner']:
                if item.attributes['delete']:
                    raise BundleError(_(
                        "{item1} (from bundle '{bundle1}') depends on item "
                        "{item2} (from bundle '{bundle2}') which is set to be deleted"
                    ).format(
                        item1=self.id,
                        bundle1=self.bundle.name,
                        item2=item.id,
                        bundle2=item.bundle.name,
                    ))
                else:
                    deps.append(item.id)
            elif item.ITEM_TYPE_NAME == "group" and item.name == self.attributes['group']:
                if item.attributes['delete']:
                    raise BundleError(_(
                        "{item1} (from bundle '{bundle1}') depends on item "
                        "{item2} (from bundle '{bundle2}') which is set to be deleted"
                    ).format(
                        item1=self.id,
                        bundle1=self.bundle.name,
                        item2=item.id,
                        bundle2=item.bundle.name,
                    ))
                else:
                    deps.append(item.id)
            elif item.ITEM_TYPE_NAME in ("directory", "symlink"):
                if is_subdirectory(item.name, self.name):
                    deps.append(item.id)
        return deps

    def sdict(self):
        path_info = PathInfo(self.node, self.name)
        if not path_info.exists:
            return None
        else:
            return {
                'target': path_info.symlink_target,
                'type': path_info.path_type,
                'owner': path_info.owner,
                'group': path_info.group,
            }

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
