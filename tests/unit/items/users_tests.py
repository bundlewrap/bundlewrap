# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from unittest import TestCase

from mock import MagicMock, patch, call

from blockwart.items import users
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
                'shell': "/bin/bash",
                'uid': 1123,
                'username': 'blockwart',
            },
        )


class FixTest(TestCase):
    """
    Tests blockwart.items.users.User.fix.
    """
    def test_fix(self):
        bundle = MagicMock()
        user = users.User(
            bundle,
            "blockwart",
            {
                'full_name': "Blöck Wart",
                'gid': 2345,
                'groups': ["group1", "group2"],
                'home': "/home/blockwart",
                'password': "secret",
                'shell': "/bin/bash",
                'uid': 1123,
            },
        )
        user.fix(MagicMock())
        self.assertEqual(
            bundle.node.run.call_args_list,
            [
                call("useradd blockwart", may_fail=True),
                call("usermod -d /home/blockwart -g 2345 -G group1,group2 -p secret -s /bin/bash -u 1123 "),
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
                'password': "secret",
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
                'password': "secret",
                'shell': "/bin/bash",
                'uid': 1123,
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
                'password': "secret",
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
                'password': "secret",
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


class LinePasswdTest(TestCase):
    """
    Tests blockwart.items.users.line_passwd.
    """
    def test_line(self):
        user = users.User(
            MagicMock(),
            "blockwart",
            {
                'full_name': "Blöck Wart",
                'gid': 2345,
                'home': "/home/blockwart",
                'password': "secret",
                'shell': "/bin/bash",
                'uid': 1123,
            },
        )
        self.assertEqual(
            user.line_passwd,
            "blockwart:x:1123:2345:Blöck Wart:/home/blockwart:/bin/bash",
        )


class LineShadowTest(TestCase):
    """
    Tests blockwart.items.users.line_shadow.
    """
    def test_line(self):
        user = users.User(
            MagicMock(),
            "blockwart",
            {
                'full_name': "Blöck Wart",
                'gid': 2345,
                'home': "/home/blockwart",
                'password': "secret",
                'shell': "/bin/bash",
                'uid': 1123,
            },
        )
        self.assertEqual(
            user.line_shadow,
            "blockwart:secret:::::::",
        )
