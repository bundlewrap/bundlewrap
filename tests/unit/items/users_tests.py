# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from unittest import TestCase

from mock import MagicMock, patch, call

from blockwart.exceptions import BundleError
from blockwart.items import ItemStatus, users
from blockwart.operations import RunResult


class GroupsForUserTest(TestCase):
    """
    Tests blockwart.items.users._groups_for_user.
    """
    def test_groups(self):
        node = MagicMock()
        result = RunResult()
        result.stdout = "group1 group2\n"
        node.run.return_value = result

        groups = users._groups_for_user(node, "jdoe")

        node.run.assert_called_once_with("id -Gn jdoe")
        self.assertEqual(groups, ["group1", "group2"])


class ParsePasswdLineTest(TestCase):
    """
    Tests blockwart.items.users._parse_passwd_line.
    """
    def test_full(self):
        self.assertEqual(
            users._parse_passwd_line(
                "blockwart:x:1123:2345:"
                "Blöck Wart,Building No,01234,56789:"
                "/home/blockwart:/bin/bash"
            ),
            {
                'full_name': "Blöck Wart",
                'gecos': "Blöck Wart,Building No,01234,56789",
                'gid': 2345,
                'home': "/home/blockwart",
                'passwd_hash': "x",
                'shell': "/bin/bash",
                'uid': 1123,
                'username': 'blockwart',
            },
        )


class AskTest(TestCase):
    """
    Tests blockwart.items.users.User.ask.
    """
    def test_user_doesnt_exist(self):
        bundle = MagicMock()
        user = users.User(
            bundle,
            "blockwart",
            {
                'full_name': "Blöck Wart",
                'gid': 2345,
                'groups': ["group1", "group2"],
                'home': "/home/blockwart",
                'password_hash': "secret",
                'shell': "/bin/bash",
                'uid': 1123,
            },
        )
        status = ItemStatus(correct=False, info={'exists': False})
        self.assertEqual(
            user.ask(status),
            "'blockwart' not found in /etc/passwd"
        )

    def test_user_will_be_deleted(self):
        bundle = MagicMock()
        user = users.User(bundle, "blockwart", {'delete': True})
        status = ItemStatus(correct=False, info={'exists': True})
        self.assertEqual(
            user.ask(status),
            "'blockwart' found in /etc/passwd. Will be deleted."
        )

    def test_passwd(self):
        bundle = MagicMock()
        user = users.User(
            bundle,
            "blockwart",
            {
                'home': "/home/blockwart",
                'full_name': "Blöck Wart",
                'gid': 2345,
                'groups': ["group1", "group2"],
                'password_hash': "topsecret",
                'shell': "/bin/bash",
                'uid': 1123,
                'use_shadow': False,
            },
        )
        status = ItemStatus(correct=False)
        status.info = {
            'exists': True,
            'full_name': "Blockwart",
            'gid': 2357,
            'groups': ["group1", "group2"],
            'home': "/home/blkwrt",
            'passwd_hash': "secret",
            'shell': "/bin/bsh",
            'uid': 1113,
            'needs_fixing': ['home', 'full_name', 'gid', 'password', 'shell', 'uid'],
        }
        self.assertEqual(
            user.ask(status),
            "home dir /home/blkwrt → /home/blockwart\n"
            "full name Blockwart → Blöck Wart\n"
            "GID 2357 → 2345\n"
            "shell /bin/bsh → /bin/bash\n"
            "UID 1113 → 1123\n"
            "password hash secret\n"
            "            → topsecret\n"
        )

    def test_shadow(self):
        bundle = MagicMock()
        user = users.User(
            bundle,
            "blockwart",
            {
                'full_name': "Blöck Wart",
                'gid': 2345,
                'groups': ["group1", "group2"],
                'home': "/home/blockwart",
                'password_hash': "secret",
                'shell': "/bin/bash",
                'uid': 1123,
            },
        )
        status = ItemStatus(correct=False)
        status.info = {
            'exists': True,
            'full_name': "Blöck Wart",
            'gid': 2345,
            'groups': ["group1", "group2"],
            'home': "/home/blockwart",
            'shadow_hash': "topsecret",
            'shell': "/bin/bash",
            'uid': 1123,
            'needs_fixing': ['password'],
        }
        self.assertEqual(
            user.ask(status),
            "password hash topsecret\n" +
            "            → secret\n"
        )

    def test_passwd_not_found(self):
        bundle = MagicMock()
        user = users.User(
            bundle,
            "blockwart",
            {
                'full_name': "Blöck Wart",
                'gid': 2345,
                'groups': ["group1", "group2"],
                'home': "/home/blockwart",
                'password_hash': "secret",
                'shell': "/bin/bash",
                'uid': 1123,
                'use_shadow': False,
            },
        )
        status = ItemStatus(correct=False)
        status.info = {
            'exists': True,
            'full_name': "Blöck Wart",
            'gid': 2345,
            'groups': ["group1", "group2"],
            'home': "/home/blockwart",
            'passwd_hash': None,
            'shell': "/bin/bash",
            'uid': 1123,
            'needs_fixing': ['password'],
        }
        self.assertEqual(
            user.ask(status),
            "password hash not found in /etc/passwd\n"
        )

    def test_shadow_not_found(self):
        bundle = MagicMock()
        user = users.User(
            bundle,
            "blockwart",
            {
                'full_name': "Blöck Wart",
                'gid': 2345,
                'groups': ["group1", "group2"],
                'home': "/home/blockwart",
                'password_hash': "secret",
                'shell': "/bin/bash",
                'uid': 1123,
            },
        )
        status = ItemStatus(correct=False)
        status.info = {
            'exists': True,
            'full_name': "Blöck Wart",
            'gid': 2345,
            'groups': ["group1", "group2"],
            'home': "/home/blockwart",
            'shadow_hash': None,
            'shell': "/bin/bash",
            'uid': 1123,
            'needs_fixing': ['password'],
        }
        self.assertEqual(
            user.ask(status),
            "password hash not found in /etc/shadow\n"
        )

    def test_groups(self):
        bundle = MagicMock()
        user = users.User(
            bundle,
            "blockwart",
            {
                'full_name': "Blöck Wart",
                'gid': 2345,
                'groups': ["group1", "group2", "group3"],
                'home': "/home/blockwart",
                'password_hash': "secret",
                'shell': "/bin/bash",
                'uid': 1123,
            },
        )
        status = ItemStatus(correct=False)
        status.info = {
            'exists': True,
            'full_name': "Blöck Wart",
            'gid': 2345,
            'groups': ["group3", "group2", "group4", "group5"],
            'home': "/home/blockwart",
            'shadow_hash': "secret",
            'shell': "/bin/bash",
            'uid': 1123,
            'needs_fixing': ['groups'],
        }
        self.assertEqual(
            user.ask(status),
            "missing groups group1\n" +
            "extra groups group4, group5\n"
        )


class FixTest(TestCase):
    """
    Tests blockwart.items.users.User.fix.
    """
    def test_fix_new(self):
        bundle = MagicMock()
        user = users.User(
            bundle,
            "blockwart",
            {
                'full_name': "Blöck Wart",
                'gid': 2345,
                'groups': ["group1", "group2"],
                'home': "/home/blockwart",
                'password_hash': "secret",
                'shell': "/bin/bash",
                'uid': 1123,
            },
        )
        status = ItemStatus(correct=False, info={
            'exists': False,
            'needs_fixing': ['home', 'gid', 'groups', 'password', 'shell', 'uid'],
        })
        user.fix(status)
        self.assertEqual(
            bundle.node.run.call_args_list,
            [
                call("useradd -d /home/blockwart -g 2345 -G group1,group2 -p secret -s /bin/bash -u 1123 blockwart", may_fail=True),
            ],
        )

    def test_fix_existing(self):
        bundle = MagicMock()
        user = users.User(
            bundle,
            "blockwart",
            {
                'full_name': "Blöck Wart",
                'gid': 2345,
                'groups': ["group1", "group2"],
                'home': "/home/blockwart",
                'password_hash': "secret",
                'shell': "/bin/bash",
                'uid': 1123,
            },
        )
        status = ItemStatus(correct=False, info={
            'exists': True,
            'needs_fixing': ['home', 'gid', 'groups', 'password', 'shell', 'uid'],
        })
        user.fix(status)
        self.assertEqual(
            bundle.node.run.call_args_list,
            [
                call("usermod -d /home/blockwart -g 2345 -G group1,group2 -p secret -s /bin/bash -u 1123 blockwart", may_fail=True),
            ],
        )

    def test_fix_delete(self):
        bundle = MagicMock()
        user = users.User(
            bundle,
            "blockwart",
            {'delete': True},
        )
        status = ItemStatus(correct=False, info={'exists': True})
        user.fix(status)
        self.assertEqual(
            bundle.node.run.call_args_list,
            [
                call("userdel blockwart", may_fail=True),
            ],
        )


class GetStatusTest(TestCase):
    """
    Tests blockwart.items.users.User.get_status.
    """
    @patch('blockwart.items.users._groups_for_user')
    def test_ok(self, _groups_for_user):
        _groups_for_user.return_value = ["group1", "group2"]
        bundle = MagicMock()
        user = users.User(
            bundle,
            "blockwart",
            {
                'full_name': "Blöck Wart",
                'gid': 2345,
                'groups': ["group1", "group2"],
                'home': "/home/blockwart",
                'password_hash': "secret",
                'shell': "/bin/bash",
                'uid': 1123,
            },
        )

        passwd_grep_result = RunResult()
        passwd_grep_result.return_code = 0
        passwd_grep_result.stdout = "blockwart:x:1123:2345:Blöck Wart:/home/blockwart:/bin/bash\n"
        shadow_grep_result = RunResult()
        shadow_grep_result.return_code = 0
        shadow_grep_result.stdout = "blockwart:secret:::::::"
        results = [shadow_grep_result, passwd_grep_result]

        def pop_result(*args, **kwargs):
            return results.pop()

        bundle.node.run.side_effect = pop_result

        status = user.get_status()
        self.assertTrue(status.correct)

    @patch('blockwart.items.users._groups_for_user')
    def test_passwd(self, _groups_for_user):
        _groups_for_user.return_value = ["group1", "group2"]
        bundle = MagicMock()
        user = users.User(
            bundle,
            "blockwart",
            {
                'full_name': "Blöck Wart",
                'gid': 2345,
                'groups': ["group1", "group2"],
                'home': "/home/blockwart",
                'password_hash': "topsecret",
                'shell': "/bin/bash",
                'uid': 1123,
                'use_shadow': False,
            },
        )

        passwd_grep_result = RunResult()
        passwd_grep_result.return_code = 0
        passwd_grep_result.stdout = "blockwart:x:666:666:Blöck Wart:/home/blockwart:/bin/bash\n"
        shadow_grep_result = RunResult()
        shadow_grep_result.return_code = 0
        shadow_grep_result.stdout = "blockwart:secret:::::::"
        results = [shadow_grep_result, passwd_grep_result]

        def pop_result(*args, **kwargs):
            return results.pop()

        bundle.node.run.side_effect = pop_result

        status = user.get_status()
        self.assertFalse(status.correct)

    def test_passwd_fail(self):
        bundle = MagicMock()
        user = users.User(
            bundle,
            "blockwart",
            {
                'full_name': "Blöck Wart",
                'gid': 2345,
                'groups': ["group1", "group2"],
                'home': "/home/blockwart",
                'password_hash': "secret",
                'shell': "/bin/bash",
                'uid': 1123,
            },
        )

        passwd_grep_result = RunResult()
        passwd_grep_result.return_code = 1

        bundle.node.run.return_value = passwd_grep_result

        status = user.get_status()
        self.assertFalse(status.correct)
        self.assertFalse(status.info['exists'])

    @patch('blockwart.items.users._groups_for_user')
    def test_shadow(self, _groups_for_user):
        _groups_for_user.return_value = ["group1", "group2"]
        bundle = MagicMock()
        user = users.User(
            bundle,
            "blockwart",
            {
                'full_name': "Blöck Wart",
                'gid': 2345,
                'groups': ["group1", "group2"],
                'home': "/home/blockwart",
                'password_hash': "secret",
                'shell': "/bin/bash",
                'uid': 1123,
            },
        )

        passwd_grep_result = RunResult()
        passwd_grep_result.return_code = 0
        passwd_grep_result.stdout = "blockwart:x:1123:2345:Blöck Wart:/home/blockwart:/bin/bash\n"
        shadow_grep_result = RunResult()
        shadow_grep_result.return_code = 0
        shadow_grep_result.stdout = "blockwart:topsecret:::::::"
        results = [shadow_grep_result, passwd_grep_result]

        def pop_result(*args, **kwargs):
            return results.pop()

        bundle.node.run.side_effect = pop_result

        status = user.get_status()
        self.assertFalse(status.correct)

    @patch('blockwart.items.users._groups_for_user')
    def test_shadow_fail(self, _groups_for_user):
        _groups_for_user.return_value = ["group1", "group2"]
        bundle = MagicMock()
        user = users.User(
            bundle,
            "blockwart",
            {
                'full_name': "Blöck Wart",
                'gid': 2345,
                'groups': ["group1", "group2"],
                'home': "/home/blockwart",
                'password_hash': "secret",
                'shell': "/bin/bash",
                'uid': 1123,
            },
        )

        passwd_grep_result = RunResult()
        passwd_grep_result.return_code = 0
        passwd_grep_result.stdout = "blockwart:x:1123:2345:Blöck Wart:/home/blockwart:/bin/bash\n"
        shadow_grep_result = RunResult()
        shadow_grep_result.return_code = 1
        results = [shadow_grep_result, passwd_grep_result]

        def pop_result(*args, **kwargs):
            return results.pop()

        bundle.node.run.side_effect = pop_result

        status = user.get_status()
        self.assertFalse(status.correct)
        self.assertEqual(status.info['shadow_hash'], None)

    def test_delete(self):
        bundle = MagicMock()
        user = users.User(
            bundle,
            "blockwart",
            {'delete': True},
        )

        passwd_grep_result = RunResult()
        passwd_grep_result.return_code = 0
        passwd_grep_result.stdout = "blockwart:x:1123:2345:Blöck Wart:/home/blockwart:/bin/bash\n"

        bundle.node.run.return_value = passwd_grep_result

        status = user.get_status()
        self.assertFalse(status.correct)
        self.assertTrue(status.info['exists'])

    @patch('blockwart.items.users._groups_for_user')
    def test_groups(self, _groups_for_user):
        _groups_for_user.return_value = ["group1", "group3"]
        bundle = MagicMock()
        user = users.User(
            bundle,
            "blockwart",
            {
                'full_name': "Blöck Wart",
                'gid': 2345,
                'groups': ["group1", "group2"],
                'home': "/home/blockwart",
                'password_hash': "secret",
                'shell': "/bin/bash",
                'uid': 1123,
            },
        )

        passwd_grep_result = RunResult()
        passwd_grep_result.return_code = 0
        passwd_grep_result.stdout = "blockwart:x:1123:2345:Blöck Wart:/home/blockwart:/bin/bash\n"
        shadow_grep_result = RunResult()
        shadow_grep_result.return_code = 0
        shadow_grep_result.stdout = "blockwart:secret:::::::"
        results = [shadow_grep_result, passwd_grep_result]

        def pop_result(*args, **kwargs):
            return results.pop()

        bundle.node.run.side_effect = pop_result

        status = user.get_status()
        self.assertFalse(status.correct)


class PatchAttributesTest(TestCase):
    """
    Tests blockwart.items.users.User.patch_attributes.
    """
    def test_without_salt(self):
        user = users.User(
            MagicMock(),
            "blockwart",
            {
                'full_name': "Blöck Wart",
                'gid': 2345,
                'groups': ["group1", "group2"],
                'password': "secret",
                'uid': 1123,
            },
        )
        self.assertEqual(
            user.attributes['password_hash'],
            "$6$uJzJlYdG$jsPJZhc5CD2lEDJZ5EBi4xNqNNXXA8EyJEe7Usez5p6H4Ing.Z9S.CQsUJfGTphLwG5qcbSyqFo2FQfcGuUpB/",
        )

    def test_with_salt(self):
        user = users.User(
            MagicMock(),
            "blockwart",
            {
                'full_name': "Blöck Wart",
                'gid': 2345,
                'groups': ["group1", "group2"],
                'password': "secret",
                'salt': "FQb/rpR/",
                'uid': 1123,
            },
        )
        self.assertEqual(
            user.attributes['password_hash'],
            "$6$FQb/rpR/$vBiqJJ8PZbRhA9TUlxOXYxNBtonojM1qa2qb338vVb58cIzGGMdJzZUkmgCXYeFQONuh4/6/m3aGyeTqizjyx1",
        )


class ValidateAttributesTest(TestCase):
    """
    Tests blockwart.items.users.User.validate_attributes.
    """
    def test_password_hash_with_password(self):
        with self.assertRaises(BundleError):
            users.User.validate_attributes(
                MagicMock(),
                "blockwart",
                {
                    'password': "secret",
                    'password_hash': "secret_hash",
                },
            )

    def test_password_hash_with_salt(self):
        with self.assertRaises(BundleError):
            users.User.validate_attributes(
                MagicMock(),
                "blockwart",
                {
                    'password_hash': "secret_hash",
                    'salt': "salt",
                },
            )

    def test_lonely_salt(self):
        with self.assertRaises(BundleError):
            users.User.validate_attributes(
                MagicMock(),
                "blockwart",
                {
                    'salt': "salt",
                },
            )

    def test_nothing(self):
        users.User.validate_attributes(
            MagicMock(),
            "blockwart",
            {},
        )

    def test_invalid_hash_method(self):
        with self.assertRaises(BundleError):
            users.User.validate_attributes(
                MagicMock(),
                "blockwart",
                {
                    'hash_method': "3des",
                    'password_hash': "secret_hash",
                },
            )

    def test_delete_with_other(self):
        with self.assertRaises(BundleError):
            users.User.validate_attributes(
                MagicMock(),
                "blockwart",
                {
                    'delete': True,
                    'password_hash': "secret_hash",
                },
            )


class ValidateNameTest(TestCase):
    """
    Tests blockwart.items.users.User.validate_name.
    """
    def test_invalid_char(self):
        with self.assertRaises(BundleError):
            users.User.validate_name(MagicMock(), "block wart")

    def test_ends_in_dash(self):
        with self.assertRaises(BundleError):
            users.User.validate_name(MagicMock(), "blockwart-")

    def test_too_long(self):
        with self.assertRaises(BundleError):
            users.User.validate_name(MagicMock(), "blockwartblockwartblockwartblockwart")

    def test_valid(self):
        users.User.validate_name(MagicMock(), "blockwart")
