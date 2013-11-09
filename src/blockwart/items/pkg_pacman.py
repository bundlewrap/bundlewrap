# -*- coding: utf-8 -*-
from __future__ import unicode_literals
from os.path import basename, join
from pipes import quote

from blockwart.exceptions import BundleError
from blockwart.items import Item, ItemStatus
from blockwart.utils.text import green, red, white
from blockwart.utils.text import mark_for_translation as _


def pkg_install(node, pkgname, operation='S'):
    return node.run("pacman --noconfirm -{} {}".format(operation,
                                                       quote(pkgname)))


def pkg_install_tarball(node, local_file):
    remote_file = "/tmp/{}".format(basename(local_file))
    node.upload(local_file, remote_file)
    pkg_install(node, remote_file, operation='U')
    node.run("rm {}".format(quote(remote_file)))


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
    BUNDLE_ATTRIBUTE_NAME = "pkg_pacman"
    DEPENDS_STATIC = []
    ITEM_ATTRIBUTES = {
        'installed': True,
        'tarball': None,
    }
    ITEM_TYPE_NAME = "pkg_pacman"
    PARALLEL_APPLY = False

    def ask(self, status):
        before = _("installed") if status.info['installed'] \
            else _("not installed")
        after = green(_("installed")) if self.attributes['installed'] \
            else red(_("not installed"))
        return "{} {} → {}\n".format(
            white(_("status"), bold=True),
            before,
            after,
        )

    def fix(self, status):
        if self.attributes['installed'] is False:
            pkg_remove(self.node, self.name)
        else:
            if self.attributes['tarball']:
                pkg_install_tarball(self.node, join(self.item_dir,
                                                    self.attributes['tarball']))
            else:
                pkg_install(self.node, self.name)

    def get_status(self):
        install_status = pkg_installed(self.node, self.name)
        item_status = (install_status == self.attributes['installed'])
        return ItemStatus(
            correct=item_status,
            info={'installed': install_status},
        )

    def validate_attributes(self, attributes):
        if not isinstance(attributes.get('installed', True), bool):
            raise BundleError("expected boolean for 'installed' on {}".format(
                self.id,
            ))
