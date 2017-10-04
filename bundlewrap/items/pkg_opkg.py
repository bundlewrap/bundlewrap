# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from pipes import quote

from bundlewrap.items.pkg import Pkg


class OpkgPkg(Pkg):
    """
    A package installed by opkg.
    """
    BUNDLE_ATTRIBUTE_NAME = "pkg_opkg"
    ITEM_TYPE_NAME = "pkg_opkg"

    @classmethod
    def block_concurrent(cls, node_os, node_os_version):
        return ["pkg_opkg"]

    def pkg_all_installed(self):
        result = self.node.run("opkg list-installed")
        for line in result.stdout.decode('utf-8').strip().split("\n"):
            if line:
                yield "{}:{}".format(self.ITEM_TYPE_NAME, line.split()[0])

    def pkg_install(self):
        self.node.run("opkg install {}".format(quote(self.name)), may_fail=True)

    def pkg_installed(self):
        result = self.node.run(
            "opkg status {} | grep ^Status: | grep installed".format(quote(self.name)),
            may_fail=True,
        )
        return result.return_code == 0

    def pkg_remove(self):
        self.node.run("opkg remove {}".format(quote(self.name)), may_fail=True)
