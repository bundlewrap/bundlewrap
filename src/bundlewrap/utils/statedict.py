# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from collections import OrderedDict
from hashlib import sha1
from json import dumps

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
