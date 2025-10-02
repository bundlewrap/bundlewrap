from base64 import b64encode
from codecs import getwriter
from contextlib import contextmanager
import hashlib
from inspect import isgenerator
from os import chmod, close, makedirs, remove
from os.path import dirname, exists
from random import shuffle
from re import compile as re_compile
import stat
from sys import stderr, stdout
from tempfile import mkstemp

from passlib.hash import apr_md5_crypt
from requests import get

from ..exceptions import DontCache, FaultUnavailable, InvalidMagicStringException


MAGIC_STRINGS_PATTERN = re_compile(r'^!([a-zA-Z0-9_]+):(.+)$')

class NO_DEFAULT: pass
MODE644 = stat.S_IRUSR | stat.S_IWUSR | stat.S_IRGRP | stat.S_IROTH
STDERR_WRITER = getwriter('utf-8')(stderr.buffer)
STDOUT_WRITER = getwriter('utf-8')(stdout.buffer)


def cached_property(prop, convert_to=None):
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
            except AttributeError as exc:
                # It's bad to raise an AttributeError from a property
                # since this will cause Python to try and use
                # __getattr__, thinking the property doesn't exist. The
                # original exception gets swallowed by this process,
                # which leads to entriely unhelpful tracebacks.
                # To prevent this, we wrap AttributeErrors in a generic
                # Exception.
                raise Exception("AttributeError in property, see above") from exc
            else:
                if convert_to:
                    return_value = convert_to(return_value)
                self._cache[prop.__name__] = return_value
        return self._cache[prop.__name__]
    return property(cache_wrapper)


def cached_property_set(prop):
    return cached_property(prop, convert_to=set)


def convert_magic_strings(repo, obj):
    if not repo.magic_string_functions:
        # If we don't have any magic string functions, we just skip this
        # altogether. This eases migration from existing implementations
        # of magic strings to the builtin methods.
        return obj

    if isinstance(obj, str):
        m = MAGIC_STRINGS_PATTERN.match(obj)
        if m:
            func_name, func_args = m.groups()
            try:
                func = repo.magic_string_functions[func_name]
            except KeyError:
                raise InvalidMagicStringException(func_name)
            else:
                with error_context(magic_string=func_name):
                    value = func(func_args)
                return value
        else:
            return obj
    elif isinstance(obj, dict):
        return {k: convert_magic_strings(repo, v) for k,v in obj.items()}
    elif isinstance(obj, list):
        return [convert_magic_strings(repo, i) for i in obj]
    elif isinstance(obj, set):
        return {convert_magic_strings(repo, i) for i in obj}
    elif isinstance(obj, tuple):
        return tuple([convert_magic_strings(repo, i) for i in obj])
    return obj


def download(url, path, timeout=60.0):
    with error_context(url=url, path=path):
        if not exists(dirname(path)):
            makedirs(dirname(path))
        if exists(path):
            chmod(path, MODE644)
        with open(path, 'wb') as f:
            r = get(url, stream=True, timeout=timeout)
            r.raise_for_status()
            for block in r.iter_content(1024):
                if not block:
                    break
                else:
                    f.write(block)


class ErrorContext(Exception):
    pass


@contextmanager
def error_context(**kwargs):
    """
    This can be used to provide context for critical exceptions. Since
    we're processing lots of different dicts, a "KeyError: foo" will
    often not be helpful, since it's not clear which dict is missing the
    key.
    """
    try:
        yield
    except Exception as exc:
        raise exc from ErrorContext(repr(kwargs))


class Fault:
    """
    A proxy object for lazy access to things that may not really be
    available at the time of use.

    This let's us gracefully skip items that require information that's
    currently not available.
    """
    def __init__(self, fault_identifier, callback, **kwargs):
        if isinstance(fault_identifier, list):
            self.id_list = fault_identifier
        else:
            self.id_list = [fault_identifier]

        for key, value in sorted(kwargs.items()):
            self.id_list.append(hash(key))
            self.id_list.append(_recursive_hash(value))

        self._available = None
        self._exc = None
        self._value = None
        self.callback = callback
        self.kwargs = kwargs

    def _repr_first(self):
        if isinstance(self.id_list, list):
            return f"<Fault: {self.id_list[0]}>"
        else:
            return f"<Fault: {self.id_list}>"

    def _repr_full(self):
        return f"<Fault: {self.id_list}>"

    def _resolve(self):
        if self._available is None:
            try:
                self._value = self.callback(**self.kwargs)
                if isinstance(self._value, Fault):
                    self._value = self._value.value
                self._available = True
            except FaultUnavailable as exc:
                self._available = False
                self._exc = exc

    def __add__(self, other):
        if isinstance(other, Fault):
            def callback():
                return self.value + other.value
            return Fault(self.id_list + other.id_list, callback)
        else:
            def callback():
                return self.value + other
            return Fault(self.id_list + ['raw {}'.format(repr(other))], callback)

    def __eq__(self, other):
        if not isinstance(other, Fault):
            return False
        else:
            return self.id_list == other.id_list

    def __hash__(self):
        return hash(tuple(self.id_list))

    def __iter__(self):
        yield from self.value

    def __len__(self):
        return len(self.value)

    def __lt__(self, other):
        if isinstance(other, Fault):
            return self.value < other.value
        else:
            return self.value < other

    def __gt__(self, other):
        if isinstance(other, Fault):
            return self.value > other.value
        else:
            return self.value > other

    def __repr__(self):
        return self._repr_full()

    def __str__(self):
        return str(self.value)

    def b64encode(self):
        def callback():
            return b64encode(self.value.encode('UTF-8')).decode('UTF-8')
        return Fault(self.id_list + ['b64encode'], callback)

    def format_into(self, format_string):
        def callback():
            return format_string.format(self.value)
        return Fault(self.id_list + ['format_into ' + format_string], callback)

    def as_htpasswd_entry(self, username):
        def callback():
            return '{}:{}'.format(
                username,
                apr_md5_crypt.encrypt(
                    self.value,
                    salt=hashlib.sha512(self.id_list[0].encode('utf-8')).hexdigest()[:8],
                ),
            )
        return Fault(self.id_list + ['as_htpasswd_entry ' + username], callback)

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
        return Fault(self.id_list + [method_name], callback)
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


def _recursive_hash(obj):
    hashes = []
    if isinstance(obj, list):
        for i in obj:
            hashes.append(_recursive_hash(i))
        return hash(tuple(hashes))
    elif isinstance(obj, set):
        for i in sorted(obj):
            hashes.append(_recursive_hash(i))
        return hash(tuple(hashes))
    elif isinstance(obj, dict):
        for k, v in sorted(obj.items()):
            hashes.append(hash(k))
            hashes.append(_recursive_hash(v))
        return hash(tuple(hashes))
    else:
        return hash(obj)


def get_file_contents(path):
    with error_context(path=path):
        with open(path, 'rb') as f:
            content = f.read()
    return content


def hash_local_file(path):
    """
    Retuns the sha1 hash of a file on the local machine.
    """
    return sha1(get_file_contents(path))


def list_starts_with(list_a, list_b):
    """
    Returns True if list_a starts with list_b.
    """
    list_a = tuple(list_a)
    list_b = tuple(list_b)
    try:
        return list_a[:len(list_b)] == list_b
    except IndexError:
        return False


def names(obj_list):
    """
    Iterator over the name properties of a given list of objects.

    repo.nodes          will give you node objects
    names(repo.nodes)   will give you node names
    """
    for obj in obj_list:
        yield obj.name


def randomize_order(obj):
    if isinstance(obj, dict):
        result = list(obj.items())
    else:
        result = list(obj)
    shuffle(result)
    return result


def sha1(data):
    """
    Returns hex SHA1 hash for input.
    """
    hasher = hashlib.sha1()
    hasher.update(data)
    return hasher.hexdigest()


class SkipList:
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
