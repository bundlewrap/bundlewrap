from shlex import quote

from bundlewrap.items.pkg import Pkg


class YumPkg(Pkg):
    """
    A package installed by yum.
    """
    BUNDLE_ATTRIBUTE_NAME = "pkg_yum"
    ITEM_TYPE_NAME = "pkg_yum"

    @classmethod
    def block_concurrent(cls, node_os, node_os_version):
        return ["pkg_dnf", "pkg_yum"]

    def pkg_all_installed(self):
        result = self.run("yum -d0 -e0 list installed")
        for line in result.stdout.decode('utf-8').strip().split("\n"):
            yield "{}:{}".format(self.ITEM_TYPE_NAME, line.split()[0].split(".")[0])

    def pkg_install(self):
        self.run("yum -d0 -e0 -y install {}".format(quote(self.name)), may_fail=True)

    def pkg_installed(self):
        result = self.run(
            "yum -d0 -e0 list installed {}".format(quote(self.name)),
            may_fail=True,
        )
        return result.return_code == 0

    def pkg_remove(self):
        self.run("yum -d0 -e0 -y remove {}".format(quote(self.name)), may_fail=True)
