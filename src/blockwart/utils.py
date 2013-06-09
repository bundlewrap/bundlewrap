from imp import find_module, load_module
from os.path import basename, dirname


def cached_property(prop):
    """
    A replacement for the property decorator that will only compute the
    attribute's value on the first call and serve cached copy from then on.
    """
    def cache_wrapper(self):
        if not hasattr(self, "_cache"):
            self._cache = {}
        if not prop in self._cache:
            self._cache[prop] = prop(self)
        return self._cache[prop]
    return property(cache_wrapper)


def import_module(path):
    """
    Imports the given file as a Python module.
    """
    mod_name = basename(path).split(".")[0]
    (f, pathname, description) = find_module(mod_name, [dirname(path)])
    return load_module(mod_name, f, pathname, description)


def mark_for_translation(s):
    return s
