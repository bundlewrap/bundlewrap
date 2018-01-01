# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from codecs import getwriter
from contextlib import contextmanager
import hashlib
from inspect import isgenerator
from os import chmod, close, makedirs, remove
from os.path import dirname, exists
import stat
from sys import stderr, stdout
from tempfile import mkstemp

from requests import get

from ..exceptions import DontCache, FaultUnavailable

__GETATTR_CODE_CACHE = {}
__GETATTR_RESULT_CACHE = {}
__GETATTR_NODEFAULT = "very_unlikely_default_value"


MODE644 = stat.S_IRUSR | stat.S_IWUSR | stat.S_IRGRP | stat.S_IROTH

try:
    STDERR_WRITER = getwriter('utf-8')(stderr.buffer)
    STDOUT_WRITER = getwriter('utf-8')(stdout.buffer)
except AttributeError:  # Python 2
    STDERR_WRITER = getwriter('utf-8')(stderr)
    STDOUT_WRITER = getwriter('utf-8')(stdout)


def cached_property(prop):
    """
    A replacement for the property decorator that will only compute the
    attribute's value on the first call and serve a cached copy from
    then on.
    """
    def cache_wrapper(self):
        if not hasattr(self, "_cache"):
            self._cache = {}
        if prop.__name__ not in self._cache:
            try:
                return_value = prop(self)
                if isgenerator(return_value):
                    return_value = tuple(return_value)
            except DontCache as exc:
                return exc.obj
            else:
                self._cache[prop.__name__] = return_value
        return self._cache[prop.__name__]
    return property(cache_wrapper)


def download(url, path):
    if not exists(dirname(path)):
        makedirs(dirname(path))
    if exists(path):
        chmod(path, MODE644)
    with open(path, 'wb') as f:
        r = get(url, stream=True)
        r.raise_for_status()
        for block in r.iter_content(1024):
            if not block:
                break
            else:
                f.write(block)


class Fault(object):
    """
    A proxy object for lazy access to things that may not really be
    available at the time of use.

    This let's us gracefully skip items that require information that's
    currently not available.
    """
    def __init__(self, callback, **kwargs):
        self._available = None
        self._exc = None
        self._value = None
        self.callback = callback
        self.kwargs = kwargs

    def _resolve(self):
        if self._available is None:
            try:
                self._value = self.callback(**self.kwargs)
                self._available = True
            except FaultUnavailable as exc:
                self._available = False
                self._exc = exc

    def __add__(self, other):
        if isinstance(other, Fault):
            def callback():
                return self.value + other.value
            return Fault(callback)
        else:
            def callback():
                return self.value + other
            return Fault(callback)

    def __len__(self):
        return len(self.value)

    def __str__(self):
        return str(self.value)

    def format_into(self, format_string):
        def callback():
            return format_string.format(self.value)
        return Fault(callback)

    @property
    def is_available(self):
        self._resolve()
        return self._available

    @property
    def value(self):
        self._resolve()
        if not self._available:
            raise self._exc
        return self._value


def _make_method_callback(method_name):
    def method(self, *args, **kwargs):
        def callback():
            return getattr(self.value, method_name)(*args, **kwargs)
        return Fault(callback)
    return method


for method_name in (
    'format',
    'lower',
    'lstrip',
    'replace',
    'rstrip',
    'strip',
    'upper',
    'zfill',
):
    setattr(Fault, method_name, _make_method_callback(method_name))


def get_file_contents(path):
    with open(path, 'rb') as f:
        content = f.read()
    return content


def get_all_attrs_from_file(path, base_env=None):
    """
    Reads all 'attributes' (if it were a module) from a source file.
    """
    if base_env is None:
        base_env = {}

    if not base_env and path in __GETATTR_RESULT_CACHE:
        # do not allow caching when passing in a base env because that
        # breaks repeated calls with different base envs for the same
        # file
        return __GETATTR_RESULT_CACHE[path]

    if path not in __GETATTR_CODE_CACHE:
        source = get_file_contents(path)
        __GETATTR_CODE_CACHE[path] = compile(source, path, mode='exec')

    code = __GETATTR_CODE_CACHE[path]
    env = base_env.copy()
    try:
        exec(code, env)
    except:
        from .ui import io
        io.stderr("Exception while executing {}".format(path))
        raise

    if not base_env:
        __GETATTR_RESULT_CACHE[path] = env

    return env


def getattr_from_file(path, attrname, base_env=None, default=__GETATTR_NODEFAULT):
    """
    Reads a specific 'attribute' (if it were a module) from a source
    file.
    """
    env = get_all_attrs_from_file(path, base_env=base_env)
    if default == __GETATTR_NODEFAULT:
        return env[attrname]
    else:
        return env.get(attrname, default)


def hash_local_file(path):
    """
    Retuns the sha1 hash of a file on the local machine.
    """
    return sha1(get_file_contents(path))


def blame_changed_paths(old_dict, new_dict, blame_dict, blame_name, defaults=False):
    def is_mergeable(value1, value2):
        if isinstance(value1, (list, set, tuple)) and isinstance(value2, (list, set, tuple)):
            return True
        elif isinstance(value1, dict) and isinstance(value2, dict):
            return True
        return False

    def map_dict_keys(d, base=None):
        if base is None:
            base = tuple()
        keys = set([base + (key,) for key in d.keys()])
        for key, value in d.items():
            if isinstance(value, dict):
                keys.update(map_dict_keys(value, base=base + (key,)))
        return keys

    new_paths = map_dict_keys(new_dict)

    # clean up removed paths from blame_dict
    for path in list(blame_dict.keys()):
        if path not in new_paths:
            del blame_dict[path]

    for path in new_paths:
        new_value = value_at_key_path(new_dict, path)
        try:
            old_value = value_at_key_path(old_dict, path)
        except KeyError:
            blame_dict[path] = (blame_name,)
        else:
            if old_value != new_value:
                if defaults or is_mergeable(old_value, new_value):
                    blame_dict[path] += (blame_name,)
                else:
                    blame_dict[path] = (blame_name,)
    return blame_dict


def names(obj_list):
    """
    Iterator over the name properties of a given list of objects.

    repo.nodes          will give you node objects
    names(repo.nodes)   will give you node names
    """
    for obj in obj_list:
        yield obj.name


def sha1(data):
    """
    Returns hex SHA1 hash for input.
    """
    hasher = hashlib.sha1()
    hasher.update(data)
    return hasher.hexdigest()


class SkipList(object):
    """
    Used to maintain a list of nodes that have already been visited.
    """
    def __init__(self, path):
        self.path = path
        if path and exists(path):
            with open(path) as f:
                self._list_items = set(f.read().strip().split("\n"))
        else:
            self._list_items = set()

    def __contains__(self, item):
        return item in self._list_items

    def add(self, item):
        if self.path:
            self._list_items.add(item)

    def dump(self):
        if self.path:
            with open(self.path, 'w') as f:
                f.write("\n".join(sorted(self._list_items)) + "\n")


@contextmanager
def tempfile():
    handle, path = mkstemp()
    close(handle)
    yield path
    remove(path)


def value_at_key_path(dict_obj, path):
    """
    Given the list of keys in `path`, recursively traverse `dict_obj`
    and return whatever is found at the end of that path.

    E.g.:

    >>> value_at_key_path({'foo': {'bar': 5}}, ['foo', 'bar'])
    5
    """
    if not path:
        return dict_obj
    else:
        return value_at_key_path(dict_obj[path[0]], path[1:])
