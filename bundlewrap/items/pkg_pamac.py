from shlex import quote

from bundlewrap.items.pkg import Pkg
from bundlewrap.exceptions import BundleError
from bundlewrap.utils.text import mark_for_translation as _


class PamacPkg(Pkg):
    """
    A package installed by pamac/pacman.
    """
    BUNDLE_ATTRIBUTE_NAME = "pkg_pamac"
    ITEM_ATTRIBUTES = {
        'installed': True,
    }
    WHEN_CREATING_ATTRIBUTES = {
        'aur': False,
    }
    ITEM_TYPE_NAME = "pkg_pamac"

    @classmethod
    def block_concurrent(cls, node_os, node_os_version):
        return ["pkg_pacman", "pkg_pamac"]

    def cdict(self):
        return {'installed': self.attributes['installed']}

    def pkg_all_installed(self):
        pkgs = self.run("pacman -Qq").stdout.decode('utf-8')
        for line in pkgs.splitlines():
            yield "{}:{}".format(self.ITEM_TYPE_NAME, line.split())

    def pkg_install(self):
        if self.when_creating['aur']:
            self.run("pamac build --no-keep --no-confirm {}".format(quote(self.name)), may_fail=True)
        else:
            self.run("pamac install --no-upgrade --no-confirm {}".format(quote(self.name)), may_fail=True)

    def pkg_installed(self):
        result = self.run(
            "pacman -Q {}".format(quote(self.name)),
            may_fail=True,
        )
        return result.return_code == 0

    def pkg_remove(self):
        self.run("pamac remove --no-confirm --unneeded --orphans {}".format(quote(self.name)), may_fail=True)

    def get_auto_deps(self, items):
        deps = []
        for item in items:
            if item == self:
                continue
            if item.ITEM_TYPE_NAME in ("pkg_pacman") and item.name == self.name:
                raise BundleError(_(
                    "{item} is declared both by pkg_pacman (in bundle {bundle_pacman}) "
                    "and pkg_pamac (in bundle {bundle_pamac})"
                ).format(
                    item=item.name,
                    bundle_pacman=item.bundle.name,
                    bundle_pamac=self.bundle.name,
                ))
        return deps
