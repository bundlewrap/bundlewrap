# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from os.path import basename, join
from pipes import quote

from bundlewrap.exceptions import BundleError
from bundlewrap.items import Item
from bundlewrap.utils.text import mark_for_translation as _


def pkg_install(node, pkgname, operation='S'):
    return node.run("pacman --noconfirm -{} {}".format(operation,
                                                       quote(pkgname)))


def pkg_install_tarball(node, local_file):
    remote_file = "/tmp/{}".format(basename(local_file))
    node.upload(local_file, remote_file)
    pkg_install(node, remote_file, operation='U')
    node.run("rm -- {}".format(quote(remote_file)))


def pkg_installed(node, pkgname):
    result = node.run(
        "pacman -Q {}".format(quote(pkgname)),
        may_fail=True,
    )
    if result.return_code != 0:
        return False
    else:
        return True


def pkg_remove(node, pkgname):
    return node.run("pacman --noconfirm -Rs {}".format(quote(pkgname)))


class PacmanPkg(Item):
    """
    A package installed by pacman.
    """
    BLOCK_CONCURRENT = ["pkg_pacman"]
    BUNDLE_ATTRIBUTE_NAME = "pkg_pacman"
    ITEM_ATTRIBUTES = {
        'installed': True,
        'tarball': None,
    }
    ITEM_TYPE_NAME = "pkg_pacman"

    def __repr__(self):
        return "<PacmanPkg name:{} installed:{} tarball:{}>".format(
            self.name,
            self.attributes['installed'],
            self.attributes['tarball'],
        )

    def cdict(self):
        # TODO/FIXME: this is bad because it ignores tarball
        return {'installed': self.attributes['installed']}

    def fix(self, status):
        if self.attributes['installed'] is False:
            pkg_remove(self.node, self.name)
        else:
            if self.attributes['tarball']:
                pkg_install_tarball(self.node, join(self.item_dir,
                                                    self.attributes['tarball']))
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
