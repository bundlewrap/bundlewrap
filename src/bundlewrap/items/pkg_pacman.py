# -*- coding: utf-8 -*-
from __future__ import unicode_literals
from os.path import basename, join
from pipes import quote

from bundlewrap.exceptions import BundleError
from bundlewrap.items import Item, ItemStatus
from bundlewrap.utils import LOG
from bundlewrap.utils.text import bold, green, red
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

    def ask(self, status):
        before = _("installed") if status.info['installed'] \
            else _("not installed")
        after = green(_("installed")) if self.attributes['installed'] \
            else red(_("not installed"))
        return "{} {} → {}\n".format(
            bold(_("status")),
            before,
            after,
        )

    def fix(self, status):
        if self.attributes['installed'] is False:
            LOG.info(_("{node}:{bundle}:{item}: removing...").format(
                bundle=self.bundle.name,
                item=self.id,
                node=self.node.name,
            ))
            pkg_remove(self.node, self.name)
        else:
            if self.attributes['tarball']:
                LOG.info(_("{node}:{bundle}:{item}: installing tarball...").format(
                    bundle=self.bundle.name,
                    item=self.id,
                    node=self.node.name,
                ))
                pkg_install_tarball(self.node, join(self.item_dir,
                                                    self.attributes['tarball']))
            else:
                LOG.info(_("{node}:{bundle}:{item}: installing...").format(
                    bundle=self.bundle.name,
                    item=self.id,
                    node=self.node.name,
                ))
                pkg_install(self.node, self.name)

    def get_status(self):
        install_status = pkg_installed(self.node, self.name)
        item_status = (install_status == self.attributes['installed'])
        return ItemStatus(
            correct=item_status,
            info={'installed': install_status},
        )

    @classmethod
    def validate_attributes(cls, bundle, item_id, attributes):
        if not isinstance(attributes.get('installed', True), bool):
            raise BundleError(_(
                "expected boolean for 'installed' on {item} in bundle '{bundle}'"
            ).format(
                bundle=bundle.name,
                item=item_id,
            ))
