import cProfile
from inspect import isgenerator
import logging
import pstats
from string import digits, letters

__GETATTR_CACHE = {}
__GETATTR_NODEFAULT = "very_unlikely_default_value"

VALID_NAME_CHARS = digits + letters + "-_.+"

LOG = logging.getLogger('blockwart')


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
    attribute's value on the first call and serve cached copy from then
    on.
    """
    def cache_wrapper(self):
        if not hasattr(self, "_cache"):
            self._cache = {}
        if not prop in self._cache:
            return_value = prop(self)
            if isgenerator(return_value):
                return_value = tuple(return_value)
            self._cache[prop] = return_value
        return self._cache[prop]
    return property(cache_wrapper)


def get_file_contents(path):
    with open(path) as f:
        content = f.read()
    return content


def get_all_attrs_from_file(path, cache_read=True, cache_write=True):
    """
    Reads all 'attributes' (if it were a module) from a source
    file.
    """
    if path not in __GETATTR_CACHE or not cache_read:
        source = get_file_contents(path)
        env = {}
        exec source in env
        if cache_write:
            __GETATTR_CACHE[path] = env
    else:
        env = __GETATTR_CACHE[path]
    return env


def getattr_from_file(path, attrname, cache_read=True, cache_write=True,
                      default=__GETATTR_NODEFAULT,
                      ):
    """
    Reads a specific 'attribute' (if it were a module) from a source
    file.
    """
    env = get_all_attrs_from_file(path, cache_read=cache_read,
                                  cache_write=cache_write)
    if default == __GETATTR_NODEFAULT:
        return env[attrname]
    else:
        return env.get(attrname, default)


def mark_for_translation(s):
    return s


def names(obj_list):
    """
    Iterator over the name properties of a given list of objects.

    repo.nodes          will give you node objects
    names(repo.nodes)   will give you node names
    """
    for obj in obj_list:
        yield obj.name


def validate_name(name):
    """
    Checks whether the given string is a valid name for a node, group,
    or bundle.
    """
    try:
        for char in name:
            assert char in VALID_NAME_CHARS
        assert not name.startswith(".")
    except AssertionError:
        return False
    return True


def ask_interactively(question, default, get_input=raw_input):
    _ = mark_for_translation
    answers = _("[Y/n]") if default else _("[y/N]")
    question = question + " " + answers + " "
    while True:
        answer = get_input(question)
        if answer.lower() in (_("y"), _("yes")) or (
            not answer and default
        ):
            return True
        elif answer.lower() in (_("n"), _("no")) or (
            not answer and not default
        ):
            return False
        print(_("Please answer with 'y(es)' or 'n(o)'."))
