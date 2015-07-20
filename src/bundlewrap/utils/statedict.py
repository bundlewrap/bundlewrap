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
except NameError:
    text_type = str

ALLOWED_VALUE_TYPES = (
    bool,
    float,
    int,
    list,
    text_type,
    tuple,
)
DIFF_MAX_INLINE_LENGTH = 36
DIFF_MAX_LINE_LENGTH = 128


def diff_keys(sdict1, sdict2):
    """
    Compares the keys of two statedicts.
    """
    if set(sdict1.keys()) != set(sdict2.keys()):
        raise ValueError(
            _("unable to compare statedicts with different keys: {} vs. {}").format(
                list(sdict1.keys()),
                list(sdict2.keys()),
            )
        )

    differing_keys = []
    for key, value in sdict1.items():
        if value != sdict2[key]:
            differing_keys.append(key)
    return differing_keys


def diff_value_int(title, value1, value2):
    return diff_value_text(
        title,
        "{}".format(value1),
        "{}".format(value2),
    )


diff_value_float = diff_value_int


def diff_value_bool(title, value1, value2):
    return diff_value_text(
        title,
        "yes" if value1 else "no",
        "yes" if value2 else "no",
    )


def diff_value_text(title, value1, value2):
    max_length = max(len(value1), len(value2))
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
    output = ""
    for line in unified_diff(
        value1.splitlines(True),
        value2.splitlines(True),
        fromfile=_("<node content>"),
        tofile=_("<bundlewrap content>"),
    ):
        suffix = ""
        line = line.rstrip("\n")
        if len(line) > DIFF_MAX_LINE_LENGTH:
            line = line[:DIFF_MAX_LINE_LENGTH]
            suffix += _(" (line truncated after {} characters)").format(DIFF_MAX_LINE_LENGTH)
        if line.startswith("+"):
            line = green(line)
        elif line.startswith("-"):
            line = red(line)
        output += line + suffix + "\n"
    return output


def hash_statedict(sdict):
    """
    Returns a canonical SHA1 hash to describe this dict.
    """
    return sha1(statedict_to_json(sdict).encode('utf-8')).hexdigest()


def statedict_to_json(sdict, pretty=False):
    """
    Returns a canonical JSON representation of the given statedict.
    """
    od = OrderedDict(sorted(sdict.items()))
    return dumps(od, indent=4 if pretty else None)


def validate_statedict(sdict):
    """
    Raises ValueError if the given statedict is invalid.
    """
    for key, value in sdict.items():
        if not isinstance(force_text(key), text_type):
            raise ValueError(_("non-text statedict key: {}").format(key))

        if type(value) not in ALLOWED_VALUE_TYPES and value is not None:
            raise ValueError(
                _("invalid statedict value for key '{k}': {v}").format(k=key, v=value)
            )

        if type(value) in (list, tuple):
            for index, element in enumerate(value):
                if type(element) not in ALLOWED_VALUE_TYPES and element is not None:
                    raise ValueError(_(
                        "invalid element #{i} in statedict key '{k}': {e}"
                    ).format(
                        e=element,
                        i=index,
                        k=key,
                    ))
