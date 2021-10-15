from os.path import basename, join
from shlex import quote

from bundlewrap.items.pkg import Pkg


class PacmanPkg(Pkg):
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

    def cdict(self):
        return {'installed': self.attributes['installed']}

    def pkg_all_installed(self):
        pkgs = self.run("pacman -Qq").stdout.decode('utf-8')
        for line in pkgs.splitlines():
            yield "{}:{}".format(self.ITEM_TYPE_NAME, line.split())

    def pkg_install(self):
        if self.attributes['aur']:
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
        self.run("pamac --no-confirm --unneeded --orphans {}".format(quote(self.name)), may_fail=True)
