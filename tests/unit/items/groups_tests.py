# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from unittest import TestCase

from mock import MagicMock, call

from blockwart.exceptions import BundleError
from blockwart.items import ItemStatus, groups
from blockwart.operations import RunResult


class ParseGroupLineTest(TestCase):
    """
    Tests blockwart.items.groups._parse_group_line.
    """
    def test_full(self):
        self.assertEqual(
            groups._parse_group_line("blockwart:x:1123:user1,user2"),
            {
                'groupname': "blockwart",
                'gid': 1123,
                'members': "user1,user2",
            },
        )


class AskTest(TestCase):
    """
    Tests blockwart.items.groups.Group.ask.
    """
    def test_group_doesnt_exist(self):
        bundle = MagicMock()
        group = groups.Group(
            bundle,
            "blockwart",
            { 'gid': 2345 },
        )
        status = ItemStatus(correct=False, info={'exists': False})
        self.assertEqual(
            group.ask(status),
            "'blockwart' not found in /etc/group"
        )

    def test_group_shouldnt_exist(self):
        bundle = MagicMock()
        group = groups.Group(
            bundle,
            "blockwart",
            {'delete': True},
        )
        status = ItemStatus(correct=False, info={'exists': True})
        self.assertEqual(
            group.ask(status),
            "'blockwart' found in /etc/group. Will be deleted."
        )

    def test_group(self):
        bundle = MagicMock()
        group = groups.Group(
            bundle,
            "blockwart",
            { 'gid': 2345 },
        )
        status = ItemStatus(correct=False)
        status.info = {
            'exists': True,
            'gid': 2357,
        }
        self.assertEqual(
            group.ask(status),
            "GID 2357 → 2345\n",
        )


class FixTest(TestCase):
    """
    Tests blockwart.items.groups.Group.fix.
    """
    def test_fix_new(self):
        bundle = MagicMock()
        group = groups.Group(
            bundle,
            "blockwart",
            { 'gid': 2345 },
        )
        status = ItemStatus(correct=False, info={'exists': False})
        group.fix(status)
        self.assertEqual(
            bundle.node.run.call_args_list,
            [
                call("groupadd -g 2345 blockwart", may_fail=True),
            ],
        )

    def test_fix_delete(self):
        bundle = MagicMock()
        group = groups.Group(
            bundle,
            "blockwart",
            {'delete': True},
        )
        status = ItemStatus(correct=False, info={'exists': True})
        group.fix(status)
        self.assertEqual(
            bundle.node.run.call_args_list,
            [
                call("groupdel blockwart", may_fail=True),
            ],
        )

    def test_fix_existing(self):
        bundle = MagicMock()
        group = groups.Group(
            bundle,
            "blockwart",
            { 'gid': 2345 },
        )
        status = ItemStatus(correct=False, info={'exists': True})
        group.fix(status)
        self.assertEqual(
            bundle.node.run.call_args_list,
            [call("groupmod -g 2345 blockwart", may_fail=True)],
        )


class GetStatusTest(TestCase):
    """
    Tests blockwart.items.groups.Group.get_status.
    """
    def test_ok(self):
        bundle = MagicMock()
        group = groups.Group(
            bundle,
            "blockwart",
            { 'gid': 2345 },
        )

        grep_result = RunResult()
        grep_result.return_code = 0
        grep_result.stdout = "blockwart:x:2345:user1,user2\n"

        bundle.node.run.return_value = grep_result

        status = group.get_status()
        self.assertTrue(status.correct)

    def test_gid(self):
        bundle = MagicMock()
        group = groups.Group(
            bundle,
            "blockwart",
            { 'gid': 2345 },
        )

        grep_result = RunResult()
        grep_result.return_code = 0
        grep_result.stdout = "blockwart:x:5432:user1,user2\n"

        bundle.node.run.return_value = grep_result

        status = group.get_status()
        self.assertFalse(status.correct)

    def test_group_fail(self):
        bundle = MagicMock()
        group = groups.Group(
            bundle,
            "blockwart",
            { 'gid': 2345 },
        )

        grep_result = RunResult()
        grep_result.return_code = 1

        bundle.node.run.return_value = grep_result

        status = group.get_status()
        self.assertFalse(status.correct)
        self.assertFalse(status.info['exists'])


class ValidateAttributesTest(TestCase):
    """
    Tests blockwart.items.groups.Group.validate_attributes.
    """
    def test_delete_with_other(self):
        with self.assertRaises(BundleError):
            groups.Group.validate_attributes(
                MagicMock(),
                "group:blockwart",
                {
                    'delete': True,
                    'gid': 2345,
                },
            )


class ValidateNameTest(TestCase):
    """
    Tests blockwart.items.groups.{User,Group}.validate_name.
    """
    def test_invalid_char(self):
        with self.assertRaises(BundleError):
            groups.Group.validate_name(MagicMock(), "block wart")

    def test_ends_in_dash(self):
        with self.assertRaises(BundleError):
            groups.Group.validate_name(MagicMock(), "blockwart-")

    def test_too_long(self):
        with self.assertRaises(BundleError):
            groups.Group.validate_name(MagicMock(), "blockwartblockwartblockwartblockwart")

    def test_valid(self):
        groups.Group.validate_name(MagicMock(), "blockwart")
