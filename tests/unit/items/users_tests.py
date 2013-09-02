# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from unittest import TestCase

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
