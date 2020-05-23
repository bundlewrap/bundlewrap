from shlex import quote

from bundlewrap.exceptions import BundleError
from bundlewrap.items import Item
from bundlewrap.utils.text import mark_for_translation as _


ZYPPER_OPTS = "--non-interactive " + \
              "--non-interactive-include-reboot-patches " + \
              "--quiet"


def pkg_install(node, pkgname):
    return node.run("zypper {} install {}".format(ZYPPER_OPTS, quote(pkgname)), may_fail=True)


def pkg_installed(node, pkgname):
    result = node.run(
        "zypper search --match-exact --installed-only "
                      "--type package {}".format(quote(pkgname)),
        may_fail=True,
    )
    if result.return_code != 0:
        return False
    else:
        return True


def pkg_remove(node, pkgname):
    return node.run("zypper {} remove {}".format(ZYPPER_OPTS, quote(pkgname)), may_fail=True)


class ZypperPkg(Item):
    """
    A package installed by zypper.
    """
    BUNDLE_ATTRIBUTE_NAME = "pkg_zypper"
    ITEM_ATTRIBUTES = {
        'installed': True,
    }
    ITEM_TYPE_NAME = "pkg_zypper"

    @classmethod
    def block_concurrent(cls, node_os, node_os_version):
        return [cls.ITEM_TYPE_NAME]

    def __repr__(self):
        return "<ZypperPkg name:{} installed:{}>".format(
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
