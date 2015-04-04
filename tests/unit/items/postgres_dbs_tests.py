# -*- coding: utf-8 -*-
from __future__ import unicode_literals
from unittest import TestCase

try:
    from unittest.mock import call, MagicMock, patch
except ImportError:
    from mock import call, MagicMock, patch

from bundlewrap.exceptions import BundleError
from bundlewrap.items import ItemStatus, postgres_dbs


class AskTest(TestCase):
    """
    Tests bundlewrap.items.postgres_dbs.PostgresDB.ask.
    """
    def test_change_owner(self):
        db = postgres_dbs.PostgresDB(MagicMock(), "foo", {'owner': "bar"})
        status = MagicMock()
        status.info = {
            'exists': True,
            'needs_fixing': ['owner'],
            'owner': "foo",
        }
        self.assertEqual(
            db.ask(status),
            "owner foo → bar",
        )

    def test_create(self):
        db = postgres_dbs.PostgresDB(MagicMock(), "foo", {'owner': "bar"})
        status = MagicMock()
        status.info = {'exists': False, 'needs_fixing': ['existence']}
        self.assertEqual(
            db.ask(status),
            "Doesn't exist. Do you want to create it?",
        )

    def test_drop(self):
        db = postgres_dbs.PostgresDB(MagicMock(), "foo", {'delete': True})
        status = MagicMock()
        status.info = {
            'exists': True,
            'needs_fixing': ['existence'],
            'owner': "bar",
        }
        self.assertEqual(
            db.ask(status),
            "Will be deleted.",
        )


class FixTest(TestCase):
    """
    Tests bundlewrap.items.postgres_dbs.PostgresDB.fix.
    """
    def test_change_owner(self):
        bundle = MagicMock()
        db = postgres_dbs.PostgresDB(
            bundle,
            "bundlewrap",
            {'owner': "bar"},
        )
        status = ItemStatus(correct=False, info={
            'exists': True,
            'needs_fixing': 'owner',
            'owner': "foo",
        })
        db.fix(status)
        self.assertEqual(
            bundle.node.run.call_args_list,
            [
                call("echo 'ALTER DATABASE bundlewrap OWNER TO bar' | "
                     "sudo -u postgres psql -nqw"),
            ],
        )

    def test_create(self):
        bundle = MagicMock()
        db = postgres_dbs.PostgresDB(
            bundle,
            "bundlewrap",
            {},
        )
        status = ItemStatus(correct=False, info={
            'exists': False,
            'needs_fixing': 'existence',
        })
        db.fix(status)
        self.assertEqual(
            bundle.node.run.call_args_list,
            [
                call("sudo -u postgres createdb -wO postgres bundlewrap"),
            ],
        )

    def test_drop(self):
        bundle = MagicMock()
        db = postgres_dbs.PostgresDB(
            bundle,
            "bundlewrap",
            {'delete': True},
        )
        status = ItemStatus(correct=False, info={
            'exists': True,
            'needs_fixing': 'existence',
        })
        db.fix(status)
        self.assertEqual(
            bundle.node.run.call_args_list,
            [
                call("sudo -u postgres dropdb -w bundlewrap"),
            ],
        )


class GetDatabasesTest(TestCase):
    """
    Tests bundlewrap.items.postgres_dbs.get_databases.
    """
    def test_get_databases(self):
        node = MagicMock()
        result = MagicMock()
        result.stdout = """postgres|postgres|UTF8|en_US.UTF-8|en_US.UTF-8|
template0|postgres|UTF8|en_US.UTF-8|en_US.UTF-8|=c/postgres
test1|root|UTF8|en_US.UTF-8|en_US.UTF-8|
"""
        node.run.return_value = result
        self.assertEqual(
            postgres_dbs.get_databases(node),
            {
                "postgres": {
                    'owner': "postgres",
                },
                "template0": {
                    'owner': "postgres",
                },
                "test1": {
                    'owner': "root",
                },
            },
        )


class GetStatusTest(TestCase):
    """
    Tests bundlewrap.items.postgres_dbs.PostgresDB.get_status.
    """
    @patch('bundlewrap.items.postgres_dbs.get_databases')
    def test_change_owner(self, get_databases):
        get_databases.return_value = {
            "bundlewrap": {
                'owner': "foo",
            },
        }
        bundle = MagicMock()
        db = postgres_dbs.PostgresDB(
            bundle,
            "bundlewrap",
            {'owner': "bar"},
        )
        status = db.get_status()
        self.assertFalse(status.correct)
        self.assertEqual(status.info['exists'], True)
        self.assertEqual(status.info['needs_fixing'], ['owner'])

    @patch('bundlewrap.items.postgres_dbs.get_databases')
    def test_create(self, get_databases):
        get_databases.return_value = {}
        bundle = MagicMock()
        db = postgres_dbs.PostgresDB(
            bundle,
            "bundlewrap",
            {'owner': "bar"},
        )
        status = db.get_status()
        self.assertFalse(status.correct)
        self.assertEqual(status.info['exists'], False)
        self.assertEqual(status.info['needs_fixing'], ['existence'])

    @patch('bundlewrap.items.postgres_dbs.get_databases')
    def test_delete(self, get_databases):
        get_databases.return_value = {
            "bundlewrap": {
                'owner': "foo",
            },
        }
        bundle = MagicMock()
        db = postgres_dbs.PostgresDB(
            bundle,
            "bundlewrap",
            {'delete': True},
        )
        status = db.get_status()
        self.assertFalse(status.correct)
        self.assertEqual(status.info['exists'], True)
        self.assertEqual(status.info['needs_fixing'], ['existence'])

    @patch('bundlewrap.items.postgres_dbs.get_databases')
    def test_ok(self, get_databases):
        get_databases.return_value = {
            "bundlewrap": {
                'owner': "foo",
            },
        }
        bundle = MagicMock()
        db = postgres_dbs.PostgresDB(
            bundle,
            "bundlewrap",
            {'owner': "foo"},
        )
        status = db.get_status()
        self.assertTrue(status.correct)
        self.assertEqual(status.info['exists'], True)
        self.assertEqual(status.info['needs_fixing'], [])


class ValidateAttributesTest(TestCase):
    """
    Tests bundlewrap.items.postgres_dbs.PostgresDB.validate_attributes.
    """
    def test_delete_ok(self):
        postgres_dbs.PostgresDB(MagicMock(), "foo", {'delete': True})
        postgres_dbs.PostgresDB(MagicMock(), "foo", {'delete': False})

    def test_delete_not_ok(self):
        with self.assertRaises(BundleError):
            postgres_dbs.PostgresDB(MagicMock(), "foo", {'delete': 0})
        with self.assertRaises(BundleError):
            postgres_dbs.PostgresDB(MagicMock(), "foo", {'delete': 1})
