# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from pipes import quote

from bundlewrap.items.pkg import Pkg


class AptPkg(Pkg):
    """
    A package installed by apt.
    """
    BLOCK_CONCURRENT = ["pkg_apt"]
    BUNDLE_ATTRIBUTE_NAME = "pkg_apt"
    ITEM_ATTRIBUTES = {
        'installed': True,
        'start_service': True,
    }
    ITEM_TYPE_NAME = "pkg_apt"

    def __repr__(self):
        # We need to override this function in order to include
        # information about 'start_service'.
        return "<{} name:{} installed:{} start_service:{}>".format(
            self.ITEM_TYPE_NAME,
            self.name,
            self.attributes['installed'],
            self.attributes['start_service'],
        )

    def cdict(self):
        # Just make sure that 'start_service' is not included in the
        # cdict, because it's never included in the sdict, either.
        return {
            'installed': self.attributes['installed'],
        }

    def pkg_all_installed(self):
        result = self.node.run("dpkg -l | grep '^ii'")
        for line in result.stdout.decode('utf-8').strip().split("\n"):
            yield "{}:{}".format(self.ITEM_TYPE_NAME, line[4:].split()[0].split(":")[0])

    def pkg_install(self):
        runlevel = "" if self.attributes['start_service'] else "RUNLEVEL=1 "
        self.node.run(
            runlevel +
            "DEBIAN_FRONTEND=noninteractive "
            "apt-get -qy -o Dpkg::Options::=--force-confold --no-install-recommends "
            "install {}".format(quote(self.name))
        )

    def pkg_installed(self):
        result = self.node.run(
            "dpkg -s {} | grep '^Status: '".format(quote(self.name)),
            may_fail=True,
        )
        return result.return_code == 0 and " installed" in result.stdout_text

    def pkg_remove(self):
        self.node.run(
            "DEBIAN_FRONTEND=noninteractive "
            "apt-get -qy purge {}".format(quote(self.name))
        )
