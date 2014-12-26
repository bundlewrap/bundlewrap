# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from pipes import quote

from bundlewrap.exceptions import BundleError
from bundlewrap.items import Item, ItemStatus
from bundlewrap.utils import LOG
from bundlewrap.utils.text import bold, green, red
from bundlewrap.utils.text import mark_for_translation as _


def pkg_install(node, pkgname, version=None):
    if version:
        pkg = "{}=={}".format(pkgname, version)
    else:
        pkg = pkgname
    return node.run("pip install -U {}".format(quote(pkg)))


def pkg_installed(node, pkgname):
    result = node.run(
        "pip freeze | grep '^{}=='".format(pkgname),
        may_fail=True,
    )
    if result.return_code != 0:
        return False
    else:
        return result.stdout.split("=")[-1].strip()


def pkg_remove(node, pkgname):
    return node.run("pip uninstall -y {}".format(quote(pkgname)))


class PipPkg(Item):
    """
    A package installed by pip.
    """
    BLOCK_CONCURRENT = ["pkg_pip"]
    BUNDLE_ATTRIBUTE_NAME = "pkg_pip"
    ITEM_ATTRIBUTES = {
        'installed': True,
        'version': None,
    }
    ITEM_TYPE_NAME = "pkg_pip"

    def __repr__(self):
        return "<PipPkg name:{} installed:{}>".format(
            self.name,
            self.attributes['installed'],
        )

    def ask(self, status):
        before = status.info['version'] if status.info['version'] \
            else _("not installed")
        target = green(self.attributes['version']) if self.attributes['version'] else \
                 green(_("installed"))
        after = target if self.attributes['installed'] \
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
            LOG.info(_("{node}:{bundle}:{item}: installing...").format(
                bundle=self.bundle.name,
                item=self.id,
                node=self.node.name,
            ))
            pkg_install(self.node, self.name, version=self.attributes['version'])

    def get_status(self):
        install_status = pkg_installed(self.node, self.name)
        item_status = (bool(install_status) == self.attributes['installed'])
        if self.attributes['version']:
            item_status = (item_status and install_status == self.attributes['version'])
        return ItemStatus(
            correct=item_status,
            info={
                'installed': bool(install_status),
                'version': None if install_status is False else install_status,
            },
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

        if 'version' in attributes and attributes.get('installed', True) is False:
            raise BundleError(_(
                "cannot set version for uninstalled package on {item} in bundle '{bundle}'"
            ).format(
                bundle=bundle.name,
                item=item_id,
            ))
