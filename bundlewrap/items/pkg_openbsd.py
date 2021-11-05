from shlex import quote
import re

from bundlewrap.exceptions import BundleError
from bundlewrap.items import Item
from bundlewrap.utils.text import mark_for_translation as _


PKGSPEC_REGEX = re.compile(r"^(.+)-(\d.*)$")


def parse_pkg_name(pkgname, line):
    matches = PKGSPEC_REGEX.match(line)
    assert matches is not None, _("Unexpected OpenBSD package name: {line}").format(line=line)

    installed_package, installed_version_and_more = matches.groups()
    assert not installed_version_and_more.endswith("-"), \
        _("Unexpected OpenBSD package name (ends in dash): {line}").format(line=line)

    if installed_package == pkgname:
        if "-" in installed_version_and_more:
            tokens = installed_version_and_more.split("-")
            installed_version = tokens[0]
            installed_flavor = "-".join(tokens[1:])
        else:
            installed_version = installed_version_and_more
            installed_flavor = ""

        return True, installed_version, installed_flavor
    else:
        return False, None, None


def pkg_install(node, pkgname, flavor, version):
    # Setting either flavor or version to None means "don't specify this
    # component". Setting flavor to the empty string means choosing the
    # "normal" flavor.
    #
    # flavor = "",     version = None:    "pkgname--"
    # flavor = "foo",  version = None:    "pkgname--foo"
    # flavor = None,   version = None:    "pkgname"          (a)
    # flavor = "",     version = "1.0":   "pkgname-1.0"      (b)
    # flavor = "foo",  version = "1.0":   "pkgname-1.0-foo"
    # flavor = None,   version = "1.0":   "pkgname-1.0"
    # flavor = None,   version = "-foo":  "pkgname--foo"  (backwards compat)
    if flavor is None and version is None:
        # Case "(a)"
        full_name = pkgname
    elif flavor == "" and version is not None:
        # Case "(b)"
        full_name = "{}-{}".format(pkgname, version)
    else:
        version_part = "-" if version is None else "-{}".format(version)
        flavor_part = "" if flavor is None else "-{}".format(flavor)
        full_name = "{}{}{}".format(pkgname, version_part, flavor_part)
    return node.run("pkg_add -r -I {}".format(full_name), may_fail=True)


def pkg_installed(node, pkgname):
    result = node.run(
        "pkg_info | cut -f 1 -d ' '",
        may_fail=True,
    )
    for line in result.stdout.decode('utf-8').strip().splitlines():
        found, installed_version, installed_flavor = parse_pkg_name(pkgname, line)
        if found:
            return installed_version, installed_flavor

    return False, None


def pkg_remove(node, pkgname):
    return node.run("pkg_delete -I -D dependencies {}".format(quote(pkgname)), may_fail=True)


class OpenBSDPkg(Item):
    """
    A package installed by pkg_add/pkg_delete.
    """
    BUNDLE_ATTRIBUTE_NAME = "pkg_openbsd"
    ITEM_ATTRIBUTES = {
        'installed': True,
        'flavor': "",
        'version': None,
    }
    ITEM_TYPE_NAME = "pkg_openbsd"

    def __repr__(self):
        return "<OpenBSDPkg name:{} installed:{}>".format(
            self.name,
            self.attributes['installed'],
        )

    @classmethod
    def block_concurrent(cls, node_os, node_os_version):
        return [cls.ITEM_TYPE_NAME]

    def cdict(self):
        cdict = self.attributes.copy()
        if not cdict['installed']:
            del cdict['flavor']
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
                self.attributes['flavor'],
                self.attributes['version']
            )

    def sdict(self):
        version, flavor = pkg_installed(self.node, self.name)
        return {
            'installed': bool(version),
            'flavor': flavor if flavor is not None else _("none"),
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
