from abc import ABCMeta, abstractmethod
from contextlib import suppress
from threading import Lock

from bundlewrap.exceptions import BundleError
from bundlewrap.items import Item
from bundlewrap.utils.text import mark_for_translation as _


class PkgInstalledLock:
    def __init__(self):
        self._access_lock = Lock()
        self._node_locks = {}

    def lock(self, node_name):
        # run this inside a lock so we can ensure we always only have
        # one Lock per node. If not, we might run into threading issues
        # when multiple threads run into this if.
        with self._access_lock:
            if node_name not in self._node_locks:
                self._node_locks[node_name] = Lock()

        return self._node_locks[node_name]


PKG_INSTALLED_LOCK = PkgInstalledLock()


class Pkg(Item, metaclass=ABCMeta):
    """
    A generic package.
    """
    ITEM_ATTRIBUTES = {
        'installed': True,
    }
    _pkg_install_cache = {}

    @classmethod
    def block_concurrent(cls, node_os, node_os_version):
        return [cls.ITEM_TYPE_NAME]

    def __repr__(self):
        return "<{} name:{} installed:{}>".format(
            self.ITEM_TYPE_NAME,
            self.name,
            self.attributes['installed'],
        )

    def fix(self, status):
        with suppress(KeyError):
            self._pkg_install_cache.get(self.node.name, set()).remove(self.id)
        if self.attributes['installed'] is False:
            self.pkg_remove()
        else:
            self.pkg_install()

    @abstractmethod
    def pkg_all_installed(self):
        raise NotImplementedError

    @abstractmethod
    def pkg_install(self):
        raise NotImplementedError

    @abstractmethod
    def pkg_installed(self):
        raise NotImplementedError

    def pkg_installed_cached(self):
        # ensure we don't run pkg_all_installed() concurrently, breaks
        # some package managers
        with PKG_INSTALLED_LOCK.lock(self.node.name):
            cache = self._pkg_install_cache.setdefault(self.node.name, set())

            if not cache:
                cache.add(None)  # make sure we don't run into this if again
                for pkgid in self.pkg_all_installed():
                    cache.add(pkgid)
        if self.pkg_in_cache(self.id, cache):
            return True
        return self.pkg_installed()

    @staticmethod
    def pkg_in_cache(pkgid, cache):
        """
        pkg_apt needs to override this for multiarch support.
        """
        return pkgid in cache

    @abstractmethod
    def pkg_remove(self):
        raise NotImplementedError

    def sdict(self):
        return {
            'installed': self.pkg_installed_cached(),
        }

    @classmethod
    def validate_attributes(cls, bundle, item_id, attributes):
        if not isinstance(attributes.get('installed', True), bool):
            raise BundleError(_(
                "expected boolean for 'installed' on {item} in bundle '{bundle}'"
            ).format(
                bundle=bundle.name,
                item=item_id,
            ))
