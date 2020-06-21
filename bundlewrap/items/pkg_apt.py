from shlex import quote

from bundlewrap.exceptions import BundleError
from bundlewrap.items.pkg import Pkg
from bundlewrap.utils.text import mark_for_translation as _


class AptPkg(Pkg):
    """
    A package installed by apt.
    """
    BUNDLE_ATTRIBUTE_NAME = "pkg_apt"
    ITEM_TYPE_NAME = "pkg_apt"
    WHEN_CREATING_ATTRIBUTES = {
        'start_service': True,
    }

    def pkg_all_installed(self):
        result = self.run("dpkg -l | grep '^ii'")
        for line in result.stdout.decode('utf-8').strip().split("\n"):
            pkg_name = line[4:].split()[0].replace(":", "_")
            yield "{}:{}".format(self.ITEM_TYPE_NAME, pkg_name)

    def pkg_install(self):
        runlevel = "" if self.when_creating['start_service'] else "RUNLEVEL=1 "
        self.run(
            runlevel +
            "DEBIAN_FRONTEND=noninteractive "
            "apt-get -qy -o Dpkg::Options::=--force-confold --no-install-recommends "
            "install {}".format(quote(self.name.replace("_", ":"))),
            may_fail=True,
        )

    def pkg_installed(self):
        result = self.run(
            "dpkg -s {} | grep '^Status: '".format(quote(self.name.replace("_", ":"))),
            may_fail=True,
        )
        return result.return_code == 0 and " installed" in result.stdout_text

    @staticmethod
    def pkg_in_cache(pkgid, cache):
        pkgtype, pkgname = pkgid.split(":")
        if "_" in pkgname:
            return pkgid in cache
        else:
            for cached_pkgid in cache:
                if cached_pkgid is None:
                    continue
                if cached_pkgid == pkgid or cached_pkgid.startswith(pkgid + ":"):
                    return True
            return False

    def pkg_remove(self):
        self.run(
            "DEBIAN_FRONTEND=noninteractive "
            "apt-get -qy purge {}".format(quote(self.name.replace("_", ":")))
        )

    @classmethod
    def validate_attributes(cls, bundle, item_id, attributes):
        super(AptPkg, cls).validate_attributes(bundle, item_id, attributes)

        if not isinstance(attributes.get('when_creating', {}).get('start_service', True), bool):
            raise BundleError(_(
                "expected boolean for 'start_service' on {item} in bundle '{bundle}'"
            ).format(
                bundle=bundle.name,
                item=item_id,
            ))
