# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from pipes import quote
import re

from bundlewrap.exceptions import BundleError
from bundlewrap.items import Item
from bundlewrap.utils.text import mark_for_translation as _


PKGSPEC_REGEX = re.compile(r"^(.+)-(\d.+)$")


def pkg_install(node, pkgname, version):
    full_name = "{}-{}".format(pkgname, version) if version else pkgname
    return node.run("pkg_add -r -I {}".format(full_name))


def pkg_installed(node, pkgname):
    result = node.run(
        "pkg_info | cut -f 1 -d ' '",
        may_fail=True,
    )
    for line in result.stdout.decode('utf-8').strip().split("\n"):
        installed_package, installed_version = PKGSPEC_REGEX.match(line).groups()
        if installed_package == pkgname:
            return installed_version
    return False


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
        'version': None,
    }
    ITEM_TYPE_NAME = "pkg_openbsd"

    def __repr__(self):
        return "<OpenBSDPkg name:{} installed:{}>".format(
            self.name,
            self.attributes['installed'],
        )

    def cdict(self):
        cdict = self.attributes.copy()
        if cdict['version'] is None or not cdict['installed']:
            del cdict['version']
        return cdict

    def fix(self, status):
        if self.attributes['installed'] is False:
            pkg_remove(self.node, self.name)
        else:
            pkg_install(self.node, self.name, self.attributes['version'])

    def sdict(self):
        version = pkg_installed(self.node, self.name)
        return {
            'installed': bool(version),
            'version': version if version else _("none"),
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
