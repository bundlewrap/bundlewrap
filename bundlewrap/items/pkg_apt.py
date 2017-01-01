# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from pipes import quote

from bundlewrap.exceptions import BundleError
from bundlewrap.items import Item
from bundlewrap.utils.text import mark_for_translation as _


def pkg_install(node, pkgname):
    return node.run("DEBIAN_FRONTEND=noninteractive "
                    "apt-get -qy -o Dpkg::Options::=--force-confold --no-install-recommends "
                    "install {}".format(quote(pkgname)))


def pkg_remove(node, pkgname):
    return node.run("DEBIAN_FRONTEND=noninteractive "
                    "apt-get -qy purge {}".format(quote(pkgname)))


class AptPkg(Item):
    """
    A package installed by apt.
    """
    BLOCK_CONCURRENT = ["pkg_apt"]
    BUNDLE_ATTRIBUTE_NAME = "pkg_apt"
    ITEM_ATTRIBUTES = {
        'installed': True,
    }
    ITEM_TYPE_NAME = "pkg_apt"
    _pkg_apt_install_cache = set()

    def __repr__(self):
        return "<AptPkg name:{} installed:{}>".format(
            self.name,
            self.attributes['installed'],
        )

    def _installed(self):
        if not self._pkg_apt_install_cache:
            self._pkg_apt_install_cache.add(None)  # make sure we don't run into this if again
            result = self.node.run("dpkg -l | grep '^ii'")
            for line in result.stdout.decode('utf-8').strip().split("\n"):
                self._pkg_apt_install_cache.add(line[4:].split()[0].split(":")[0])
        if self.name in self._pkg_apt_install_cache:
            return True

        result = self.node.run(
            "dpkg -s {} | grep '^Status: '".format(quote(self.name)),
            may_fail=True,
        )
        return result.return_code == 0 and " installed" in result.stdout_text

    def fix(self, status):
        try:
            self._pkg_apt_install_cache.remove(self.name)
        except KeyError:
            pass
        if self.attributes['installed'] is False:
            pkg_remove(self.node, self.name)
        else:
            pkg_install(self.node, self.name)

    def sdict(self):
        return {
            'installed': self._installed(),
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
