# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from os.path import basename, join
from pipes import quote

from bundlewrap.items.pkg import Pkg


class PacmanPkg(Pkg):
    """
    A package installed by pacman.
    """
    BLOCK_CONCURRENT = ["pkg_pacman"]
    BUNDLE_ATTRIBUTE_NAME = "pkg_pacman"
    ITEM_ATTRIBUTES = {
        'installed': True,
        'tarball': None,
    }
    ITEM_TYPE_NAME = "pkg_pacman"

    def cdict(self):
        # TODO/FIXME: this is bad because it ignores tarball
        # (However, that's not part of the node's state, so bw won't
        # "fix" it anyway, so ... I guess we can live with that.)
        return {'installed': self.attributes['installed']}

    def pkg_all_installed(self):
        pkgs = self.node.run("pacman -Qq").stdout.decode('utf-8')
        for line in pkgs.splitlines():
            yield line.strip()

    def pkg_install(self):
        if self.attributes['tarball']:
            local_file = join(self.item_dir, self.attributes['tarball'])
            remote_file = "/tmp/{}".format(basename(local_file))
            self.node.upload(local_file, remote_file)
            self.node.run("pacman --noconfirm -U {}".format(quote(remote_file)))
            self.node.run("rm -- {}".format(quote(remote_file)))
        else:
            self.node.run("pacman --noconfirm -S {}".format(quote(self.name)))

    def pkg_installed(self):
        result = self.node.run(
            "pacman -Q {}".format(quote(self.name)),
            may_fail=True,
        )
        return result.return_code == 0

    def pkg_remove(self):
        self.node.run("pacman --noconfirm -Rs {}".format(quote(self.name)))
