# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from pipes import quote

from bundlewrap.items.pkg import Pkg


class SnapPkg(Pkg):
    """
    A package installed by snap.
    """
    BUNDLE_ATTRIBUTE_NAME = "pkg_snap"
    ITEM_TYPE_NAME = "pkg_snap"

    def pkg_all_installed(self):
        result = self.node.run("snap list")
        for line in result.stdout.decode('utf-8').strip().split("\n"):
            yield "{}:{}".format(self.ITEM_TYPE_NAME, line.split()[0].split(" ")[0])

    def pkg_install(self):
        self.node.run("snap install {}".format(quote(self.name)), may_fail=True)

    def pkg_installed(self):
        result = self.node.run(
            "snap list {}".format(quote(self.name)),
            may_fail=True,
        )
        return result.return_code == 0

    def pkg_remove(self):
        self.node.run("snap remove {}".format(quote(self.name)), may_fail=True)
