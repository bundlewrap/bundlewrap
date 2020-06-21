from os.path import basename, join
from shlex import quote

from bundlewrap.items.pkg import Pkg


class PacmanPkg(Pkg):
    """
    A package installed by pacman.
    """
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
        pkgs = self.run("pacman -Qq").stdout.decode('utf-8')
        for line in pkgs.splitlines():
            yield "{}:{}".format(self.ITEM_TYPE_NAME, line.split())

    def pkg_install(self):
        if self.attributes['tarball']:
            local_file = join(self.item_dir, self.attributes['tarball'])
            remote_file = "/tmp/{}".format(basename(local_file))
            self.node.upload(local_file, remote_file)
            self.run("pacman --noconfirm -U {}".format(quote(remote_file)), may_fail=True)
            self.run("rm -- {}".format(quote(remote_file)))
        else:
            self.run("pacman --noconfirm -S {}".format(quote(self.name)), may_fail=True)

    def pkg_installed(self):
        result = self.run(
            "pacman -Q {}".format(quote(self.name)),
            may_fail=True,
        )
        return result.return_code == 0

    def pkg_remove(self):
        self.run("pacman --noconfirm -Rs {}".format(quote(self.name)), may_fail=True)
