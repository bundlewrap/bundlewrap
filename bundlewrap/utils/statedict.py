# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from collections import OrderedDict
from difflib import unified_diff
from hashlib import sha1
from json import dumps

from .text import bold, green, red
from .text import force_text, mark_for_translation as _


try:
    text_type = unicode
    byte_type = str
except NameError:
    text_type = str
    byte_type = bytes

DIFF_MAX_INLINE_LENGTH = 36
DIFF_MAX_LINE_LENGTH = 128


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
    for line in unified_diff(
        value1.splitlines(True),
        value2.splitlines(True),
        fromfile=_("<node>"),
        tofile=_("<bundlewrap>"),
    ):
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
    byte_type: diff_value_text,
    float: diff_value_int,
    int: diff_value_int,
    list: diff_value_list,
    set: diff_value_list,
    text_type: diff_value_text,
    tuple: diff_value_list,
}


def diff_value(title, value1, value2):
    value_type = type(value1)
    assert value_type == type(value2)
    diff_func = TYPE_DIFFS[value_type]
    return diff_func(title, value1, value2)


def hash_statedict(sdict):
    """
    Returns a canonical SHA1 hash to describe this dict.
    """
    return sha1(statedict_to_json(sdict).encode('utf-8')).hexdigest()


def order_dict(d):
    """
    Return an ordered dict from the given standard dict.
    """
    if not isinstance(d, dict):
        return d
    new_d = OrderedDict({})
    for key, value in sorted(d.items()):
        if isinstance(value, dict):
            new_d[key] = order_dict(value)
        elif isinstance(value, list) or isinstance(value, tuple):
            new_d[key] = [order_dict(item) for item in value]
        else:
            new_d[key] = value
    return new_d


def statedict_to_json(sdict, pretty=False):
    """
    Returns a canonical JSON representation of the given statedict.
    """
    if sdict is None:
        return ""
    else:
        return dumps(order_dict(sdict), indent=4 if pretty else None)


def validate_statedict(sdict):
    """
    Raises ValueError if the given statedict is invalid.
    """
    if sdict is None:
        return
    for key, value in sdict.items():
        if not isinstance(force_text(key), text_type):
            raise ValueError(_("non-text statedict key: {}").format(key))

        if type(value) not in TYPE_DIFFS and value is not None:
            raise ValueError(
                _("invalid statedict value for key '{k}': {v}").format(k=key, v=value)
            )

        if type(value) in (list, tuple):
            for index, element in enumerate(value):
                if type(element) not in TYPE_DIFFS and element is not None:
                    raise ValueError(_(
                        "invalid element #{i} in statedict key '{k}': {e}"
                    ).format(
                        e=element,
                        i=index,
                        k=key,
                    ))
