from os.path import join, split
from shlex import quote

from bundlewrap.exceptions import BundleError
from bundlewrap.items import Item
from bundlewrap.utils.text import mark_for_translation as _


def pkg_install(node, pkgname, version=None):
    if version:
        pkgname = "{}=={}".format(pkgname, version)
    pip_path, pkgname = split_path(node, pkgname)
    return node.run("{} install -U {}".format(quote(pip_path), quote(pkgname)), may_fail=True)


def pkg_installed(node, pkgname):
    pip_path, pkgname = split_path(node, pkgname)
    result = node.run(
        "{} freeze | grep -i '^{}=='".format(quote(pip_path), pkgname),
        may_fail=True,
    )
    if result.return_code != 0:
        return False
    else:
        return result.stdout_text.split("=")[-1].strip()


def pkg_remove(node, pkgname):
    pip_path, pkgname = split_path(node, pkgname)
    return node.run("{} uninstall -y {}".format(quote(pip_path), quote(pkgname)), may_fail=True)


class PipPkg(Item):
    """
    A package installed by pip.
    """
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

    def cdict(self):
        cdict = {'installed': self.attributes['installed']}
        if self.attributes.get('version') is not None:
            cdict['version'] = self.attributes['version']
        return cdict

    def get_auto_deps(self, items):
        for item in items:
            if item == self:
                continue
            if (
                item.ITEM_TYPE_NAME == self.ITEM_TYPE_NAME and
                item.name.lower() == self.name.lower()
            ):
                raise BundleError(_(
                    "{item1} (from bundle '{bundle1}') has name collision with "
                    "{item2} (from bundle '{bundle2}')"
                ).format(
                    item1=item.id,
                    bundle1=item.bundle.name,
                    item2=self.id,
                    bundle2=self.bundle.name,
                ))
        return []

    def fix(self, status):
        if self.attributes['installed'] is False:
            pkg_remove(self.node, self.name)
        else:
            pkg_install(self.node, self.name, version=self.attributes['version'])

    def sdict(self):
        install_status = pkg_installed(self.node, self.name)
        return {
            'installed': bool(install_status),
            'version': None if install_status is False else install_status,
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

        if 'version' in attributes and attributes.get('installed', True) is False:
            raise BundleError(_(
                "cannot set version for uninstalled package on {item} in bundle '{bundle}'"
            ).format(
                bundle=bundle.name,
                item=item_id,
            ))


def split_path(node, pkgname):
    virtualenv, pkgname = split(pkgname)
    pip_path = join(virtualenv, "bin", "pip") if virtualenv else node.pip_command
    return pip_path, pkgname
