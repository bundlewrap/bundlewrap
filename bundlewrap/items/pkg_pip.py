from json import loads
from os.path import join, split
from shlex import quote

from bundlewrap.exceptions import BundleError
from bundlewrap.items import Item
from bundlewrap.utils.text import mark_for_translation as _


class PipPkg(Item):
    """
    A package installed by pip.
    """
    BUNDLE_ATTRIBUTE_NAME = "pkg_pip"
    ITEM_ATTRIBUTES = {
        'break_system_packages': False,
        'installed': True,
        'version': None,
    }
    ITEM_TYPE_NAME = "pkg_pip"

    @classmethod
    def block_concurrent(cls, node_os, node_os_version):
        return [cls.ITEM_TYPE_NAME]

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
            self._pkg_remove(self.name)
        else:
            self._pkg_install(self.name, version=self.attributes['version'])

    def sdict(self):
        install_status = self._pkg_installed(self.name)
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

    @classmethod
    def validate_name(cls, bundle, name):
        if "_" in split(name)[1]:
            raise BundleError(
                f"Underscores are not allowed in pkg_pip names "
                f"because pip will convert them to dashes anyway. "
                f"Just use dashes. (pkg_pip:{name} in bundle {bundle.name})"
            )

    def _pkg_install(self, pkgname, version=None):
        if version:
            pkgname = "{}=={}".format(pkgname, version)
        pip_path, pkgname = self._split_path(pkgname)
        return self.run(
            "{} install {} -U {}".format(
                quote(pip_path),
                '--break-system-packages' if self.attributes['break_system_packages'] else '',
                quote(pkgname),
            ),
            may_fail=True,
        )

    def _pkg_installed(self, pkgname):
        pip_path, pkgname = self._split_path(pkgname)

        result = self.run(
            "{} list -v --format json".format(quote(pip_path)),
            may_fail=True,
        )
        if result.return_code != 0:
            return False
        else:
            pkgs = loads(result.stdout_text)
            for pkg_desc in pkgs:
                if (
                    pkg_desc['installer'] == 'pip' and
                    pkg_desc['name'].lower() == pkgname.lower()
                ):
                    return pkg_desc['version']
            return False

    def _pkg_remove(self, pkgname):
        pip_path, pkgname = self._split_path(pkgname)
        return self.run(
            "{} uninstall {} -y {}".format(
                quote(pip_path),
                '--break-system-packages' if self.attributes['break_system_packages'] else '',
                quote(pkgname),
            ),
            may_fail=True,
        )

    def _split_path(self, pkgname):
        virtualenv, pkgname = split(pkgname)
        pip_path = join(virtualenv, "bin", "pip") if virtualenv else self.node.pip_command
        return pip_path, pkgname
