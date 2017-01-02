# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from pipes import quote

from bundlewrap.items.pkg import Pkg


class YumPkg(Pkg):
    """
    A package installed by yum.
    """
    BLOCK_CONCURRENT = ["pkg_dnf", "pkg_yum"]
    BUNDLE_ATTRIBUTE_NAME = "pkg_yum"
    ITEM_TYPE_NAME = "pkg_yum"

    def pkg_all_installed(self):
        result = self.node.run("yum -d0 -e0 list installed")
        for line in result.stdout.decode('utf-8').strip().split("\n"):
            yield line.split()[0].split(".")[0]

    def pkg_install(self):
        self.node.run("yum -d0 -e0 -y install {}".format(quote(self.name)))

    def pkg_installed(self):
        result = self.node.run(
            "yum -d0 -e0 list installed {}".format(quote(self.name)),
            may_fail=True,
        )
        return result.return_code == 0

    def pkg_remove(self):
        self.node.run("yum -d0 -e0 -y remove {}".format(quote(self.name)))
