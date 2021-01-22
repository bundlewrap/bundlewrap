from shlex import quote

from bundlewrap.exceptions import BundleError
from bundlewrap.items import Item
from bundlewrap.utils.text import mark_for_translation as _


def parse_pkg_name(pkgname, line):
    # Contains the assumption that version may not contain '-', which is covered
    # according to the FreeBSD docs (Section 5.2.4, "PKGNAMEPREFIX and PKGNAMESUFFIX")
    installed_package, _sep, installed_version = line.rpartition('-')
    assert installed_package != "", _(
        "Unexpected FreeBSD package name: {line}").format(line=line)
    return installed_package == pkgname, installed_version


def pkg_install(node, pkgname, version):
    # Setting version to None means "don't specify version".
    if version is None:
        full_name = pkgname
    else:
        full_name = pkgname + "-" + version

    return node.run("pkg install -y {}".format(full_name), may_fail=True)


def pkg_installed(node, pkgname):
    result = node.run(
        "pkg info | cut -f 1 -d ' '",
        may_fail=True,
    )
    for line in result.stdout.decode('utf-8').strip().splitlines():
        found, installed_version = parse_pkg_name(pkgname, line)
        if found:
            return installed_version

    return False


def pkg_remove(node, pkgname):
    return node.run("pkg delete -y -R {}".format(quote(pkgname)), may_fail=True)


class FreeBSDPkg(Item):
    """
    A package installed via pkg install/pkg delete.
    """
    BUNDLE_ATTRIBUTE_NAME = "pkg_freebsd"
    ITEM_ATTRIBUTES = {
        'installed': True,
        'version': None,
    }
    ITEM_TYPE_NAME = "pkg_freebsd"

    def __repr__(self):
        return "<FreeBSDPkg name:{} installed:{}>".format(
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
            pkg_install(
                self.node,
                self.name,
                self.attributes['version']
            )

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
