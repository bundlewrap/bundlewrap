from shlex import quote

from bundlewrap.items.pkg import Pkg


class ApkPkg(Pkg):
    """
    A package installed by apk.
    """

    BUNDLE_ATTRIBUTE_NAME = "pkg_apk"
    ITEM_TYPE_NAME = "pkg_apk"

    @property
    def quoted(self):
        return quote(self.name)

    def pkg_all_installed(self):
        pkgs = self.run("apk list --installed").stdout.decode("utf-8")
        for line in pkgs.splitlines():
            pkg_name = line.split()[0]
            yield f"{self.ITEM_TYPE_NAME}:{pkg_name}"

    def pkg_install(self):
        self.run(f"apk add {self.quoted}", may_fail=True)

    def pkg_installed(self):
        result = self.run(f"apk info --installed {self.quoted}", may_fail=True)
        return result.return_code == 0 and self.quoted in result.stdout_text

    def pkg_remove(self):
        self.run(f"apk del {self.quoted}", may_fail=True)
