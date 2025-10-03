from re import compile

from ..exceptions import InvalidMagicStringException
from ..metadata import atomic
from . import error_context
from .dicts import _Atomic

MAGIC_STRINGS_PATTERN = compile(r"^!([a-zA-Z0-9_]+):(.+)$")


def convert_magic_strings(repo, obj):
    if not repo.magic_string_functions:
        # If we don't have any magic string functions, we just skip this
        # altogether. This eases migration from existing implementations
        # of magic strings to the builtin methods.
        return obj

    is_atomic = isinstance(obj, _Atomic)

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
                    obj = func(func_args)
    elif isinstance(obj, dict):
        obj = {k: convert_magic_strings(repo, v) for k, v in obj.items()}
    elif isinstance(obj, list):
        obj = [convert_magic_strings(repo, i) for i in obj]
    elif isinstance(obj, set):
        obj = {convert_magic_strings(repo, i) for i in obj}
    elif isinstance(obj, tuple):
        obj = tuple([convert_magic_strings(repo, i) for i in obj])
    if is_atomic:
        return atomic(obj)
    return obj
