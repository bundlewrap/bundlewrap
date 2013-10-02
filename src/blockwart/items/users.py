# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from blockwart.items import Item


def _parse_passwd_line(line):
    """
    Parses a line from /etc/passwd and returns the information as a
    dictionary.
    """
    result = dict(zip(
        ('username', 'password', 'uid', 'gid', 'gecos', 'home', 'shell'),
        line.lstrip().split(":"),
    ))
    result['uid'] = int(result['uid'])
    result['gid'] = int(result['gid'])
    result['full_name'] = result['gecos'].split(",")[0]
    return result


class User(Item):
    """
    A user account.
    """
    BUNDLE_ATTRIBUTE_NAME = "users"
    DEPENDS_STATIC = []
    ITEM_ATTRIBUTES = {
        'full_name': "",
        'gid': None,
        'home': None,
        'password': "!",
        'shell': "",
        'uid': None,
    }
    ITEM_TYPE_NAME = "user"


    @property
    def line_passwd(self):
        return ':'.join([
            self.name,
            'x',
            str(self.attributes['uid']),
            str(self.attributes['gid']),
            self.attributes['full_name'],
            self.attributes['home'],
            self.attributes['shell'],
        ])

    @property
    def line_shadow(self):
        return ':'.join([
            self.name,
            self.attributes['password'],
            '',  # last password change
            '',  # minimum password age
            '',  # maximum password age
            '',  # warning period
            '',  # inactivity period
            '',  # expiration date
            '',  # undefined/reserved
        ])
