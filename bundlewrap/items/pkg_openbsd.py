# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from pipes import quote

from bundlewrap.exceptions import BundleError
from bundlewrap.items import Item
from bundlewrap.utils.text import mark_for_translation as _


def pkg_install(node, pkgname):
    return node.run("pkg_add -r -I {}".format(quote(pkgname)))


def pkg_installed(node, pkgname):
    result = node.run(
        "pkg_info | cut -f 1 -d ' ' | grep '^{}$'".format(pkgname),
        may_fail=True,
    )
    if result.return_code != 0:
        return False
    else:
        return True


def pkg_remove(node, pkgname):
    return node.run("pkg_delete -I -D dependencies {}".format(quote(pkgname)))


class OpenBSDPkg(Item):
    """
    A package installed by pkg_add/pkg_delete.
    """
    BLOCK_CONCURRENT = ["pkg_openbsd"]
    BUNDLE_ATTRIBUTE_NAME = "pkg_openbsd"
    ITEM_ATTRIBUTES = {
        'installed': True,
    }
    ITEM_TYPE_NAME = "pkg_openbsd"

    def __repr__(self):
        return "<OpenBSDPkg name:{} installed:{}>".format(
            self.name,
            self.attributes['installed'],
        )

    def fix(self, status):
        if self.attributes['installed'] is False:
            pkg_remove(self.node, self.name)
        else:
            pkg_install(self.node, self.name)

    def sdict(self):
        return {
            'installed': pkg_installed(self.node, self.name),
        }

    @classmethod
    def validate_attributes(cls, bundle, item_id, attributes):
        if not isinstance(attributes.get('installed', True), bool):
            raise BundleError(_(
                "expected boolean for 'installed' on {item} in bundle '{bundle}'"
            ).format(
                bundle=bundle.name,
                item=item_id,
            ))
