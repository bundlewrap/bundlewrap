# -*- coding: utf-8 -*-
from __future__ import unicode_literals
from unittest import TestCase

try:
    from unittest.mock import call, MagicMock, patch
except ImportError:
    from mock import call, MagicMock, patch

from bundlewrap.exceptions import BundleError
from bundlewrap.items import ItemStatus, postgres_roles


class AskTest(TestCase):
    """
    Tests bundlewrap.items.postgres_roles.PostgresRole.ask.
    """
    def test_change_password(self):
        role = postgres_roles.PostgresRole(MagicMock(), "bw", {
            'superuser': False,
            'password': "new",
        })
        status = MagicMock()
        status.info = {
            'exists': True,
            'needs_fixing': ['superuser'],
            'password_hash': "old",
            'superuser': False,
        }
        self.assertEqual(
            role.ask(status),
            "password hash old → md5d4011cb5bc2abb087f5ae9d3ca846423",
        )

    def test_change_superuser(self):
        role = postgres_roles.PostgresRole(MagicMock(), "bw", {'superuser': False})
        status = MagicMock()
        status.info = {
            'exists': True,
            'needs_fixing': ['superuser'],
            'password_hash': "foo",
            'superuser': True,
        }
        self.assertEqual(
            role.ask(status),
            "superuser True → False",
        )

    def test_create(self):
        role = postgres_roles.PostgresRole(MagicMock(), "bw", {})
        status = MagicMock()
        status.info = {
            'exists': False,
            'needs_fixing': ['existence'],
        }
        self.assertEqual(
            role.ask(status),
            "Doesn't exist. Do you want to create it?",
        )

    def test_drop(self):
        role = postgres_roles.PostgresRole(MagicMock(), "bw", {'delete': True})
        status = MagicMock()
        status.info = {
            'exists': True,
            'needs_fixing': ['existence'],
        }
        self.assertEqual(
            role.ask(status),
            "Will be deleted.",
        )


class FixTest(TestCase):
    """
    Tests bundlewrap.items.postgres_roles.PostgresRole.fix.
    """
    def test_change_superuser(self):
        bundle = MagicMock()
        role = postgres_roles.PostgresRole(
            bundle,
            "bundlewrap",
            {'superuser': True},
        )
        status = ItemStatus(correct=False, info={
            'exists': True,
            'needs_fixing': ['superuser'],
            'password_hash': "foo",
            'superuser': False,
        })
        role.fix(status)
        self.assertEqual(
            bundle.node.run.call_args_list,
            [
                call("echo \"ALTER ROLE 'bundlewrap' WITH SUPERUSER\""
                     " | sudo -u postgres psql -nqw"),
            ],
        )

    def test_create(self):
        bundle = MagicMock()
        role = postgres_roles.PostgresRole(
            bundle,
            "bundlewrap",
            {},
        )
        status = ItemStatus(correct=False, info={
            'exists': False,
            'needs_fixing': ['existence'],
            'password_hash': "foo",
            'superuser': False,
        })
        role.fix(status)
        self.assertEqual(
            bundle.node.run.call_args_list,
            [
                call("echo \"CREATE ROLE 'bundlewrap' WITH NOSUPERUSER\" | sudo -u postgres psql -nqw"),
            ],
        )

    def test_drop(self):
        bundle = MagicMock()
        role = postgres_roles.PostgresRole(
            bundle,
            "bundlewrap",
            {'delete': True},
        )
        status = ItemStatus(correct=False, info={
            'exists': True,
            'needs_fixing': ['existence'],
            'password_hash': "foo",
            'superuser': False,
        })
        role.fix(status)
        self.assertEqual(
            bundle.node.run.call_args_list,
            [
                call("sudo -u postgres dropuser -w bundlewrap"),
            ],
        )


class GetRoleTest(TestCase):
    """
    Tests bundlewrap.items.postgres_roles.get_role.
    """
    def test_empty_role(self):
        node = MagicMock()
        result = MagicMock()
        result.stdout = "\n"
        node.run.return_value = result
        self.assertEqual(
            postgres_roles.get_role(node, "bw"),
            {},
        )

    def test_get_role(self):
        node = MagicMock()
        result = MagicMock()
        result.stdout = """rolsuper|f
rolpassword|foo
"""
        node.run.return_value = result
        self.assertEqual(
            postgres_roles.get_role(node, "bw"),
            {
                'superuser': False,
                'password_hash': "foo",
            },
        )


class GetStatusTest(TestCase):
    """
    Tests bundlewrap.items.postgres_roles.PostgresRole.get_status.
    """
    @patch('bundlewrap.items.postgres_roles.get_role')
    def test_change_superuser(self, get_role):
        get_role.return_value = {
            'password_hash': "foo",
            'superuser': True,
        }
        bundle = MagicMock()
        role = postgres_roles.PostgresRole(
            bundle,
            "bundlewrap",
            {'superuser': False},
        )
        status = role.get_status()
        self.assertFalse(status.correct)
        self.assertEqual(status.info['exists'], True)
        self.assertEqual(status.info['needs_fixing'], ['superuser'])

    @patch('bundlewrap.items.postgres_roles.get_role')
    def test_create(self, get_role):
        get_role.return_value = {}
        bundle = MagicMock()
        role = postgres_roles.PostgresRole(
            bundle,
            "bundlewrap",
            {'superuser': True},
        )
        status = role.get_status()
        self.assertFalse(status.correct)
        self.assertEqual(status.info['exists'], False)
        self.assertEqual(status.info['needs_fixing'], ['existence'])

    @patch('bundlewrap.items.postgres_roles.get_role')
    def test_delete(self, get_role):
        get_role.return_value = {
            'password_hash': "foo",
            'superuser': False,
        }
        bundle = MagicMock()
        role = postgres_roles.PostgresRole(
            bundle,
            "bundlewrap",
            {'delete': True},
        )
        status = role.get_status()
        self.assertFalse(status.correct)
        self.assertEqual(status.info['exists'], True)
        self.assertEqual(status.info['needs_fixing'], ['existence'])

    @patch('bundlewrap.items.postgres_roles.get_role')
    def test_ok(self, get_role):
        get_role.return_value = {
            'password_hash': "foo",
            'superuser': False,
        }
        bundle = MagicMock()
        role = postgres_roles.PostgresRole(
            bundle,
            "bundlewrap",
            {'superuser': False},
        )
        status = role.get_status()
        self.assertTrue(status.correct)
        self.assertEqual(status.info['exists'], True)
        self.assertEqual(status.info['needs_fixing'], [])


class ValidateAttributesTest(TestCase):
    """
    Tests bundlewrap.items.postgres_roles.PostgresRole.validate_attributes.
    """
    def test_delete_ok(self):
        postgres_roles.PostgresRole(MagicMock(), "bw", {'delete': True})
        postgres_roles.PostgresRole(MagicMock(), "bw", {'delete': False})

    def test_delete_not_ok(self):
        with self.assertRaises(BundleError):
            postgres_roles.PostgresRole(MagicMock(), "bw", {'delete': 0})
        with self.assertRaises(BundleError):
            postgres_roles.PostgresRole(MagicMock(), "bw", {'delete': 1})
