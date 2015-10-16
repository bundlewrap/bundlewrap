# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from pipes import quote

from bundlewrap.exceptions import BundleError
from bundlewrap.items import Item
from bundlewrap.utils.text import mark_for_translation as _


def pkg_install(node, pkgname):
    return node.run("yum -d0 -e0 -y install {}".format(quote(pkgname)))


def pkg_installed(node, pkgname):
    result = node.run(
        "yum -d0 -e0 list installed {}".format(quote(pkgname)),
        may_fail=True,
    )
    if result.return_code != 0:
        return False
    else:
        return True


def pkg_remove(node, pkgname):
    return node.run("yum -d0 -e0 -y remove {}".format(quote(pkgname)))


class YumPkg(Item):
    """
    A package installed by yum.
    """
    BLOCK_CONCURRENT = ["pkg_yum"]
    BUNDLE_ATTRIBUTE_NAME = "pkg_yum"
    ITEM_ATTRIBUTES = {
        'installed': True,
    }
    ITEM_TYPE_NAME = "pkg_yum"

    def __repr__(self):
        return "<YumPkg name:{} installed:{}>".format(
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
