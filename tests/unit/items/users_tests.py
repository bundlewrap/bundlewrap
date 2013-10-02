# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from unittest import TestCase

from mock import MagicMock

from blockwart.items import users


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
                'password': "x",
                'shell': "/bin/bash",
                'uid': 1123,
                'username': 'blockwart',
            },
        )


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
