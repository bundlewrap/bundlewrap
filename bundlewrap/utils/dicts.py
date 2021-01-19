from copy import copy
from difflib import unified_diff
from hashlib import sha1
from json import dumps, JSONEncoder

from tomlkit import document as toml_document

from . import Fault
from .text import bold, green, red
from .text import force_text, mark_for_translation as _


DIFF_MAX_INLINE_LENGTH = 36
DIFF_MAX_LINE_LENGTH = 1024


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


def diff_keys(sdict1, sdict2):
    """
    Compares the keys of two statedicts and returns the keys with
    differing values.

    Note that only keys in the first statedict are considered. If a key
    only exists in the second one, it is disregarded.
    """
    if sdict1 is None:
        return []
    if sdict2 is None:
        return sdict1.keys()
    differing_keys = []
    for key, value in sdict1.items():
        if value != sdict2[key]:
            differing_keys.append(key)
    return differing_keys


def diff_value_bool(title, value1, value2):
    return diff_value_text(
        title,
        "yes" if value1 else "no",
        "yes" if value2 else "no",
    )


def diff_value_int(title, value1, value2):
    return diff_value_text(
        title,
        "{}".format(value1),
        "{}".format(value2),
    )


def diff_value_list(title, value1, value2):
    if isinstance(value1, set):
        value1 = sorted(value1)
        value2 = sorted(value2)
    else:
        # convert tuples and create copies of lists before possibly
        # appending stuff later on (see below)
        value1 = list(value1)
        value2 = list(value2)
    # make sure that *if* we have lines, the last one will also end with
    # a newline
    if value1:
        value1.append("")
    if value2:
        value2.append("")
    return diff_value_text(
        title,
        "\n".join([str(i) for i in value1]),
        "\n".join([str(i) for i in value2]),
    )


def diff_value_text(title, value1, value2):
    max_length = max(len(value1), len(value2))
    value1, value2 = force_text(value1), force_text(value2)
    if (
        "\n" not in value1 and
        "\n" not in value2
    ):
        if max_length < DIFF_MAX_INLINE_LENGTH:
            return "{}  {} → {}".format(
                bold(title),
                red(value1),
                green(value2),
            )
        elif max_length < DIFF_MAX_LINE_LENGTH:
            return "{}  {}\n{}→  {}".format(
                bold(title),
                red(value1),
                " " * (len(title) - 1),
                green(value2),
            )
    output = bold(title) + "\n"
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
    return output


TYPE_DIFFS = {
    bool: diff_value_bool,
    bytes: diff_value_text,
    float: diff_value_int,
    int: diff_value_int,
    list: diff_value_list,
    set: diff_value_list,
    str: diff_value_text,
    tuple: diff_value_list,
}


def diff_value(title, value1, value2):
    value_type = type(value1)
    assert value_type == type(value2), "cannot compare {} with {}".format(
        repr(value1),
        repr(value2),
    )
    diff_func = TYPE_DIFFS[value_type]
    return diff_func(title, value1, value2)


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


def map_dict_keys(dict_obj, _base=None):
    """
    Return a set of key paths for the given dict. E.g.:

        >>> map_dict_keys({'foo': {'bar': 1}, 'baz': 2})
        set([('foo', 'bar'), ('baz',)])
    """
    if _base is None:
        _base = tuple()
    keys = set([_base + (key,) for key in dict_obj.keys()])
    for key, value in dict_obj.items():
        if isinstance(value, dict):
            keys.update(map_dict_keys(value, _base=_base + (key,)))
    return keys


def extra_paths_in_dict(dict_obj, paths):
    """
    Returns all paths in dict_obj that don't start with any of the
    given paths.

        >>> filter_dict({'a': 1, 'b': {'c': 1}}, {('b', 'c')})
        {('a',)}
    """
    result = set()
    for actual_path in map_dict_keys(dict_obj):
        for allowed_path in paths:
            if (
                actual_path[:len(allowed_path)] == allowed_path or
                allowed_path[:len(actual_path)] == actual_path
            ):
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
            (
                isinstance(value, list) or
                isinstance(value, set) or
                isinstance(value, tuple)
            )
        ):
            extended = base[key][:]
            extended.extend(value)
            merged[key] = extended
        elif (
            merge and
            isinstance(base[key], tuple) and
            (
                isinstance(value, list) or
                isinstance(value, set) or
                isinstance(value, tuple)
            )
        ):
            merged[key] = base[key] + tuple(value)
        elif (
            merge and
            isinstance(base[key], set) and
            (
                isinstance(value, list) or
                isinstance(value, set) or
                isinstance(value, tuple)
            )
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
        for index in range(len(full_dict)):
            full_dict_element = full_dict[index]
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


class COLLECTION_OF_STRINGS: pass
class TUPLE_OF_INTS: pass


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
        elif allowed_types == TUPLE_OF_INTS:
            if not isinstance(value, tuple):
                raise ValueError(_("key '{k}' is {i}, but should be a tuple").format(
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

        if not isinstance(value, tuple(TYPE_DIFFS.keys())) and value is not None:
            raise ValueError(_(
                "invalid statedict value for key '{k}': {v}"
            ).format(
                k=key,
                v=repr(value),
            ))

        if isinstance(value, (list, tuple)):
            for index, element in enumerate(value):
                if not isinstance(element, tuple(TYPE_DIFFS.keys())) and element is not None:
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
