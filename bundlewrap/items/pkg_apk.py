# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from pipes import quote

from bundlewrap.items.pkg import Pkg


class ApkPkg(Pkg):
    """
    A package installed by apk.
    """
    BLOCK_CONCURRENT = ["pkg_apk"]
    BUNDLE_ATTRIBUTE_NAME = "pkg_apk"
    ITEM_TYPE_NAME = "pkg_apk"

    def pkg_all_installed(self):
        result = self.node.run("apk info")
        for line in result.stdout.decode('utf-8').strip().split("\n"):
            yield line

    def pkg_install(self):
        self.node.run("apk -f add {}".format(quote(self.name)))

    def pkg_installed(self):
        result = self.node.run(
            "apk info | grep ^{}$".format(self.name),
            may_fail=True,
        )
        return result.return_code == 0

    def pkg_remove(self):
        self.node.run("apk -f del {}".format(quote(self.name)))
