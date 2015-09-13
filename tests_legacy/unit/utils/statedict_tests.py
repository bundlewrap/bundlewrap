# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from unittest import TestCase

from bundlewrap.utils import statedict


EXAMPLE_SDICT = {
    'int': 1,
    'float': 1.0,
    'text': "täxt",
    'tuple': (1, 2, 3, False, None),
    'list': ["one", 2.0, 3, True],
    'bool': True,
    'none': None,
}
EXAMPLE_HASH = "fba40ac6145215c4fe60030cfe0c8aee5be410db"
EXAMPLE_JSON = "{\"bool\": true, \"float\": 1.0, \"int\": 1, \"list\": [\"one\", 2.0, 3, true], \"none\": null, \"text\": \"t\\u00e4xt\", \"tuple\": [1, 2, 3, false, null]}"


class DiffKeysTest(TestCase):
    """
    Tests bundlewrap.utils.statedict.diff_keys.
    """
    def test_different_keys(self):
        with self.assertRaises(KeyError):
            statedict.diff_keys(
                {'foo': "bar"},
                {'bar': "foo"},
            )

    def test_identical(self):
        self.assertEqual(
            statedict.diff_keys(
                {'foo': "bar"},
                {'foo': "bar"},
            ),
            [],
        )

    def test_difference(self):
        self.assertEqual(
            statedict.diff_keys(
                {'foo': "bar", 'baz': 1},
                {'foo': "bar", 'baz': 2},
            ),
            ['baz'],
        )


class HashStateDictTest(TestCase):
    """
    Tests bundlewrap.utils.statedict.hash_statedict.
    """
    def test_hash(self):
        self.assertEqual(
            statedict.hash_statedict(EXAMPLE_SDICT),
            EXAMPLE_HASH,
        )


class StateDictToJSONTest(TestCase):
    """
    Tests bundlewrap.utils.statedict.statedict_to_json.
    """
    def test_json(self):
        self.assertEqual(
            statedict.statedict_to_json(EXAMPLE_SDICT),
            EXAMPLE_JSON,
        )


class ValidateStateDictTest(TestCase):
    """
    Tests bundlewrap.utils.statedict.validate_statedict.
    """
    def test_ok(self):
        statedict.validate_statedict(EXAMPLE_SDICT)

    def test_invalid_keys(self):
        with self.assertRaises(ValueError):
            statedict.validate_statedict({1: 2})
        with self.assertRaises(ValueError):
            statedict.validate_statedict({1.0: 2})
        with self.assertRaises(ValueError):
            statedict.validate_statedict({True: 2})
        with self.assertRaises(ValueError):
            statedict.validate_statedict({None: 2})
        with self.assertRaises(ValueError):
            statedict.validate_statedict({(): 2})
        with self.assertRaises(ValueError):
            statedict.validate_statedict({object(): 2})

    def test_invalid_values(self):
        with self.assertRaises(ValueError):
            statedict.validate_statedict({'foo': {}})
        with self.assertRaises(ValueError):
            statedict.validate_statedict({'foo': object()})
        with self.assertRaises(ValueError):
            statedict.validate_statedict({'foo': [object()]})
        with self.assertRaises(ValueError):
            statedict.validate_statedict({'foo': (object(),)})
        with self.assertRaises(ValueError):
            statedict.validate_statedict({'foo': "föö".encode('utf-8')})
