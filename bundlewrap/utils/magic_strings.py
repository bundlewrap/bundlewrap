from inspect import Parameter, signature
from re import compile

from ..exceptions import InvalidMagicStringException
from ..metadata import atomic
from . import error_context
from .dicts import _Atomic

MAGIC_STRING_NAME = r"[a-zA-Z0-9_]+"
MAGIC_STRING_NAME_PATTERN = compile(r"^" + MAGIC_STRING_NAME + r"$")
MAGIC_STRINGS_PATTERN = compile(r"^!(" + MAGIC_STRING_NAME + r"):(.*)$")

_ACCEPTS_NODE = {}


def _accepts_node(func):
    """
    True if func can be called with node=..., i.e. it has a `node`
    parameter or takes **kwargs. Cached, signature() is not cheap.
    """
    try:
        return _ACCEPTS_NODE[func]
    except KeyError:
        pass
    except TypeError:  # unhashable callable
        return False
    try:
        params = signature(func).parameters
    except (TypeError, ValueError):  # builtins
        result = False
    else:
        param = params.get('node')
        result = (
            (param is not None and param.kind != Parameter.POSITIONAL_ONLY)
            or any(p.kind == Parameter.VAR_KEYWORD for p in params.values())
        )
    _ACCEPTS_NODE[func] = result
    return result


def convert_magic_strings(repo, obj, node=None):
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
                    if node is not None and _accepts_node(func):
                        obj = func(func_args, node=node)
                    else:
                        obj = func(func_args)
    elif isinstance(obj, dict):
        obj = {k: convert_magic_strings(repo, v, node=node) for k, v in obj.items()}
    elif isinstance(obj, list):
        obj = [convert_magic_strings(repo, i, node=node) for i in obj]
    elif isinstance(obj, set):
        obj = {convert_magic_strings(repo, i, node=node) for i in obj}
    elif isinstance(obj, tuple):
        obj = tuple([convert_magic_strings(repo, i, node=node) for i in obj])
    if is_atomic:
        return atomic(obj)
    return obj
