import cProfile
import pstats


class PrintProfiler(object):
    def __enter__(self):
        self.pr = cProfile.Profile()
        self.pr.enable()

    def __exit__(self, type, value, traceback):
        self.pr.disable()
        pstats.Stats(self.pr).sort_stats('cumulative').print_stats()


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


def getattr_from_file(path, attrname):
    """
    Reads a specific 'attribute' (if it were a module) from a source file.
    """
    with open(path) as f:
        source = f.read()
    env = {}
    exec source in env
    return env[attrname]


def mark_for_translation(s):
    return s
