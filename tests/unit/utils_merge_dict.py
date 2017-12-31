# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from bundlewrap.utils import blame_changed_paths, merge_dict


def test_blame_and_merge():
    dict1 = {
        'key1': 11,
        'key2': {
            'key21': 121,
            'key22': 122,
        },
        'key3': {
            'key31': {
                'key311': [1311],
            },
        },
    }
    dict2 = {
        'key2': {
            'key21': 221,
        },
        'key3': {
            'key31': {
                'key311': [2311],
                'key312': 2312,
            },
        },
        'key4': 24,
    }
    from pprint import pprint
    blame = {}
    merged = merge_dict(
        {},
        dict1,
    )
    blame_changed_paths(
        {},
        merged,
        blame,
        "dict1",
    )
    pprint(blame)
    merged2 = merge_dict(
        merged,
        dict2,
    )
    blame_changed_paths(
        merged,
        merged2,
        blame,
        "dict2",
    )
    pprint(blame)

    should = {
        ('key1',): ("dict1",),
        ('key2',): ("dict1", "dict2"),
        ('key2', 'key21'): ("dict2",),
        ('key2', 'key22'): ("dict1",),
        ('key3',): ("dict1", "dict2"),
        ('key3', 'key31',): ("dict1", "dict2"),
        ('key3', 'key31', 'key311'): ("dict1", "dict2"),
        ('key3', 'key31', 'key312'): ("dict2",),
        ('key4',): ("dict2",),
    }
    pprint(should)
    assert blame == should

    assert merged2 == {
        'key1': 11,
        'key2': {
            'key21': 221,
            'key22': 122,
        },
        'key3': {
            'key31': {
                'key311': [1311, 2311],
                'key312': 2312,
            },
        },
        'key4': 24,
    }
