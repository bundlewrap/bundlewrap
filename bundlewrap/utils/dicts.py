from copy import copy
from difflib import unified_diff
from hashlib import sha1
from json import dumps, JSONEncoder

from tomlkit import document as toml_document

from . import Fault
from .text import bold, green, red, yellow
from .text import force_text, mark_for_translation as _


DIFF_MAX_INLINE_LENGTH = 36
DIFF_MAX_LINE_LENGTH = 1024


class _MISSING_KEY:
    pass


class _Atomic:
    """
    This and the following related classes are used to mark objects as
    non-mergeable for the purposes of merge_dict().
    """
    pass

class _AtomicDict(dict, _Atomic): pass
class _AtomicList(list, _Atomic): pass
class _AtomicSet(set, _Atomic): pass
class _AtomicTuple(tuple, _Atomic): pass


ATOMIC_TYPES = {
    dict: _AtomicDict,
    list: _AtomicList,
    set: _AtomicSet,
    tuple: _AtomicTuple,
}


def dict_to_toml(dict_obj):
    toml_doc = toml_document()
    for key, value in dict_obj.items():
        if isinstance(value, tuple):
            toml_doc[key] = list(value)
        elif isinstance(value, set):
            toml_doc[key] = sorted(value)
        elif isinstance(value, dict):
            toml_doc[key] = dict_to_toml(value)
        else:
            toml_doc[key] = value
    return toml_doc


def diff_keys(dict1, dict2):
    differing_keys = set()
    for key in set(dict1.keys()) | set(dict2.keys()):
        try:
            if dict1[key] != dict2[key]:
                differing_keys.add(key)
        except KeyError:
            differing_keys.add(key)
    return differing_keys


def diff_normalize_bool(value):
    return "yes" if value else "no"


def diff_normalize_bytes(value):
    return value.decode('utf-8', 'backslashreplace')


def diff_normalize_list(value):
    if isinstance(value, set):
        value = sorted(value)
    else:
        # convert tuples and create copies of lists before possibly
        # appending stuff later on (see below)
        value = list(value)
    # make sure that *if* we have lines, the last one will also end with
    # a newline
    if value:
        value.append("")
    return "\n".join([str(i) for i in value])


TYPE_DIFF_NORMALIZE = {
    bool: diff_normalize_bool,
    bytes: diff_normalize_bytes,
    float: str,
    int: str,
    list: diff_normalize_list,
    type(None): str,
    set: diff_normalize_list,
    tuple: diff_normalize_list,
}
VALID_STATEDICT_TYPES = tuple(TYPE_DIFF_NORMALIZE.keys()) + (str,)


def diff_normalize(value):
    if isinstance(value, str):
        return value
    try:
        normalize = TYPE_DIFF_NORMALIZE[type(value)]
    except KeyError:
        raise TypeError(_("unable to diff {} ({})").format(
            repr(value),
            type(value),
        ))
    return normalize(value)


def diff_text(value1, value2):
    max_length = max(len(value1), len(value2))
    value1, value2 = force_text(value1), force_text(value2)
    if (
        "\n" not in value1 and
        "\n" not in value2
    ):
        if max_length < DIFF_MAX_INLINE_LENGTH:
            return "{} → {}".format(
                red(value1),
                green(value2),
            )
        elif max_length < DIFF_MAX_LINE_LENGTH:
            return "  {}\n→ {}".format(
                red(value1),
                green(value2),
            )
    output = ""
    for line in tuple(unified_diff(
        value1.splitlines(True),
        value2.splitlines(True),
    ))[2:]:
        suffix = ""
        if len(line) > DIFF_MAX_LINE_LENGTH:
            suffix += _(" (line truncated after {} characters)").format(DIFF_MAX_LINE_LENGTH)
        if not line.endswith("\n"):
            suffix += _(" (no newline at end of file)")
        line = line[:DIFF_MAX_LINE_LENGTH].rstrip("\n")
        if line.startswith("+"):
            line = green(line)
        elif line.startswith("-"):
            line = red(line)
        output += line + suffix + "\n"
    return output.rstrip("\n")


def diff_value(value1, value2):
    if value1 == _MISSING_KEY:
        value1 = yellow(_("<missing>"))
    if value2 == _MISSING_KEY:
        value2 = yellow(_("<missing>"))
    return diff_text(diff_normalize(value1), diff_normalize(value2))


def diff_dict(dict1, dict2, skip_missing_in_target=False):
    def handle_multiline(key, diff):
        if "\n" in diff:
            return bold(key) + "\n" + diff + "\n"
        else:
            return bold(key) + "  " + diff + "\n"

    output = ""
    if dict1 is None and dict2 is None:
        return ""
    elif dict1 is None:
        for key, value in sorted(dict2.items()):
            output += handle_multiline(key, green(str(value)))
    elif dict2 is None:
        for key, value in sorted(dict1.items()):
            output += handle_multiline(key, red(str(value)))
    else:
        for key in sorted(diff_keys(dict1, dict2)):
            if skip_missing_in_target and key not in dict2:
                # this is used to hide anything not present in a cdict
                # and thus not relevant to the diff/user
                continue
            value1 = dict1.get(key, _MISSING_KEY)
            value2 = dict2.get(key, _MISSING_KEY)
            diff = diff_value(value1, value2)
            output += handle_multiline(key, diff)

    return output


def dict_to_text(dict_obj, value_color=str):
    output = ""
    for key, value in sorted(dict_obj.items()):
        value = diff_normalize(value)
        if "\n" in value:
            output += bold(key) + "\n"
            for line in value.splitlines():
                output += value_color(line) + "\n"
        else:
            output += bold(key) + "  " + value_color(value) + "\n"
    return output.rstrip("\n")


class FaultResolvingJSONEncoder(JSONEncoder):
    def default(self, obj):
        if isinstance(obj, Fault):
            return self.default(obj.value)
        elif isinstance(obj, set):
            return sorted(obj)
        else:
            return JSONEncoder.default(self, obj)


def hash_statedict(sdict):
    """
    Returns a canonical SHA1 hash to describe this dict.
    """
    return sha1(statedict_to_json(sdict).encode('utf-8')).hexdigest()


def map_dict_keys(dict_obj, leaves_only=False, _base=None,):
    """
    Return a set of key paths for the given dict. E.g.:

        >>> map_dict_keys({'foo': {'bar': 1}, 'baz': 2})
        set([('foo', 'bar'), ('baz',)])
    """
    if _base is None:
        _base = ()
    keys = set()
    for key, value in dict_obj.items():
        is_dict = isinstance(value, dict)
        if is_dict:
            keys.update(map_dict_keys(
                value,
                leaves_only=leaves_only,
                _base=_base + (key,),
            ))
        if not is_dict or not leaves_only:
            keys.add(_base + (key,))
    return keys


def extra_paths_in_dict(dict_obj, paths):
    """
    Returns all paths in dict_obj that don't start with any of the
    given paths.

        >>> extra_paths_in_dict({'a': 1, 'b': {'c': 1}}, {('b', 'c')})
        {('a',)}
    """
    result = set()
    for actual_path in map_dict_keys(dict_obj, leaves_only=True):
        for allowed_path in paths:
            if actual_path[:len(allowed_path)] == allowed_path:
                break
        else:
            result.add(actual_path)
    return result


def merge_dict(base, update):
    """
    Recursively merges the base dict into the update dict.
    """
    if not isinstance(update, dict):
        return update

    merged = base.copy()

    for key, value in update.items():
        merge = (
            key in base and
            not isinstance(value, _Atomic) and
            not isinstance(base[key], _Atomic)
        )
        if merge and isinstance(base[key], dict):
            merged[key] = merge_dict(base[key], value)
        elif (
            merge and
            isinstance(base[key], list) and
            isinstance(value, (list, set, tuple))
        ):
            extended = base[key][:]
            extended.extend(value)
            merged[key] = extended
        elif (
            merge and
            isinstance(base[key], tuple) and
            isinstance(value, (list, set, tuple))
        ):
            merged[key] = base[key] + tuple(value)
        elif (
            merge and
            isinstance(base[key], set) and
            isinstance(value, (list, set, tuple))
        ):
            merged[key] = base[key].union(set(value))
        else:
            # If we don't copy here, we end up with dicts from groups in
            # node metadata. Not an issue per se, but a nasty pitfall
            # when users do things like this in items.py:
            #
            #    my_dict = node.metadata.get('foo', {})
            #    my_dict['bar'] = 'baz'
            #
            # The expectation here is to be able to mangle my_dict
            # because it is only relevant for the current node. However,
            # if 'foo' has only been defined in a group, we end up
            # mangling that dict for every node in the group.
            # Since we can't really force users to .copy() in this case
            # (although they should!), we have to do it here.
            merged[key] = copy(value)

    return merged


def reduce_dict(full_dict, template_dict):
    """
    Take a large dict and recursively remove all keys that are not
    present in the template dict. Also descends into lists.

    >>> full_dict = {
        'a': [{
            'b': 1,
            'c': 2,  # this will be removed from final result
        }],
        'd': 3,
    }
    >>> template_dict = {
        'a': [{
            'b': None,
        }],
        'd': None,
        'e': None,
    }
    >>> reduce_dict(full_dict, template_dict)
    {
        'a': [{
            'b': 1,
        }],
        'd': 3,
    }
    """
    if isinstance(full_dict, list):
        if not isinstance(template_dict, list):
            return full_dict
        result = []
        for index, full_dict_element in enumerate(full_dict):
            try:
                template_dict_element = template_dict[index]
            except IndexError:
                template_dict_element = full_dict_element
            result.append(reduce_dict(full_dict_element, template_dict_element))
        return result
    elif isinstance(full_dict, dict):
        if not isinstance(template_dict, dict):
            return full_dict
        result = {}
        for key, value in full_dict.items():
            if key in template_dict:
                result[key] = reduce_dict(value, template_dict[key])
        return result
    else:
        return full_dict


def statedict_to_json(sdict, pretty=False):
    """
    Returns a canonical JSON representation of the given statedict.
    """
    if sdict is None:
        return ""
    else:
        return dumps(
            sdict,
            cls=FaultResolvingJSONEncoder,
            indent=4 if pretty else None,
            sort_keys=True,
        )


def normalize_dict(dict_obj, types):
    result = {}
    for key, value in dict_obj.items():
        try:
            normalize = types[key]
        except KeyError:
            result[key] = value
        else:
            result[key] = normalize(value)
    return result


class COLLECTION_OF_STRINGS: pass
class LIST_OR_TUPLE_OF_INTS: pass


def validate_dict(candidate, schema, required_keys=None):
    if not isinstance(candidate, dict):
        raise ValueError(_("not a dict: {}").format(repr(candidate)))
    for key, value in candidate.items():
        if key not in schema:
            raise ValueError(_("illegal key: {}").format(key))
        allowed_types = schema[key]
        if allowed_types == COLLECTION_OF_STRINGS:
            if not isinstance(value, (list, set, tuple)):
                raise ValueError(_("key '{k}' is {i}, but should be one of: {t}").format(
                    k=key,
                    i=type(value),
                    t=(list, set, tuple),
                ))
            for inner_value in value:
                if not isinstance(inner_value, str):
                    raise ValueError(_("non-string member in '{k}': {v}").format(
                        k=key,
                        v=repr(inner_value),
                    ))
        elif allowed_types == LIST_OR_TUPLE_OF_INTS:
            if not isinstance(value, (list, tuple)):
                raise ValueError(_("key '{k}' is {i}, but should be a tuple or list").format(
                    k=key,
                    i=type(value),
                ))
            for inner_value in value:
                if not isinstance(inner_value, int):
                    raise ValueError(_("non-int member in '{k}': {v}").format(
                        k=key,
                        v=repr(inner_value),
                    ))
        elif not isinstance(value, allowed_types):
            raise ValueError(_("key '{k}' is {i}, but should be one of: {t}").format(
                k=key,
                i=type(value),
                t=allowed_types,
            ))
    for key in required_keys or []:
        if key not in candidate:
            raise ValueError(_("missing required key: {}").format(key))


def validate_statedict(sdict):
    """
    Raises ValueError if the given statedict is invalid.
    """
    if sdict is None:
        return
    for key, value in sdict.items():
        if not isinstance(force_text(key), str):
            raise ValueError(_("non-text statedict key: {}").format(key))

        if not isinstance(value, VALID_STATEDICT_TYPES) and value is not None:
            raise ValueError(_(
                "invalid statedict value for key '{k}': {v}"
            ).format(
                k=key,
                v=repr(value),
            ))

        if isinstance(value, (list, tuple)):
            for index, element in enumerate(value):
                if not isinstance(element, VALID_STATEDICT_TYPES) and element is not None:
                    raise ValueError(_(
                        "invalid element #{i} in statedict key '{k}': {e}"
                    ).format(
                        e=repr(element),
                        i=index,
                        k=key,
                    ))


def delete_key_at_path(d, path):
    if len(path) == 1:
        del d[path[0]]
    else:
        delete_key_at_path(d[path[0]], path[1:])


def replace_key_at_path(d, path, new_key):
    if len(path) == 1:
        value = d[path[0]]
        del d[path[0]]
        d[new_key] = value
    else:
        replace_key_at_path(d[path[0]], path[1:], new_key)


def set_key_at_path(d, path, value):
    if len(path) == 0:
        d.update(value)
    elif len(path) == 1:
        d[path[0]] = value
    else:
        if path[0] not in d:  # setdefault doesn't work with tomlkit
            d[path[0]] = {}
        set_key_at_path(d[path[0]], path[1:], value)


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
        nested_dict = dict_obj[path[0]]
        remaining_path = path[1:]
        if remaining_path and not isinstance(nested_dict, dict):
            raise KeyError("/".join(path))
        else:
            return value_at_key_path(nested_dict, remaining_path)
