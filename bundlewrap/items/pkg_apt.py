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
    ITEM_TYPE_NAME = "pkg_apt"

    def pkg_all_installed(self):
        result = self.node.run("dpkg -l | grep '^ii'")
        for line in result.stdout.decode('utf-8').strip().split("\n"):
            yield line[4:].split()[0].split(":")[0]

    def pkg_install(self):
        self.node.run(
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
