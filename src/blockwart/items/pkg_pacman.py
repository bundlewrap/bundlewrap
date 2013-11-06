# -*- coding: utf-8 -*-
from __future__ import unicode_literals
from pipes import quote

from blockwart.exceptions import BundleError
from blockwart.items import Item, ItemStatus
from blockwart.utils.text import green, red, white
from blockwart.utils.text import mark_for_translation as _


def pkg_install(node, pkgname):
    return node.run("pacman --noconfirm -S {}".format(quote(pkgname)))


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
    }
    ITEM_TYPE_NAME = "pkg_pacman"

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
