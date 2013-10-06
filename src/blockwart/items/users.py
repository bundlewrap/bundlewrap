# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from pipes import quote

from blockwart.items import Item, ItemStatus


def _groups_for_user(node, username):
    """
    Returns the list of group names for the given username on the given
    node.
    """
    idcmd = node.run("id -Gn {}".format(username))
    return idcmd.stdout.strip().split(" ")


def _parse_passwd_line(line):
    """
    Parses a line from /etc/passwd and returns the information as a
    dictionary.
    """
    result = dict(zip(
        ('username', 'password', 'uid', 'gid', 'gecos', 'home', 'shell'),
        line.strip().split(":"),
    ))
    result['uid'] = int(result['uid'])
    result['gid'] = int(result['gid'])
    result['full_name'] = result['gecos'].split(",")[0]
    del result['password']  # nothing useful here
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
        'groups': [],
        'home': None,
        'password': "!",
        'shell': "/bin/bash",
        'uid': None,
    }
    ITEM_TYPE_NAME = "user"

    def fix(self, status):
        self.node.run("useradd {}".format(self.name), may_fail=True)
        self.node.run("usermod "
            "-d {home} "
            "-g {gid} "
            "-G {groups} "
            "-p {password} "
            "-s {shell} "
            "-u {uid} ".format(
                home=quote(self.attributes['home']),
                gid=self.attributes['gid'],
                groups=quote(",".join(self.attributes['groups'])),
                password=quote(self.attributes['password']),
                shell=quote(self.attributes['shell']),
                uid=self.attributes['uid'],
            )
        )


    def get_status(self):
        # verify content of /etc/passwd
        passwd_grep_result = self.node.run(
            "grep -e '^{}:' /etc/passwd".format(self.name),
            may_fail=True,
        )
        if passwd_grep_result.return_code != 0 or \
                passwd_grep_result.stdout.strip() != self.line_passwd:
            return ItemStatus(correct=False)

        # verify content of /etc/shadow
        shadow_grep_result = self.node.run(
            "grep -e '^{}:' /etc/shadow".format(self.name),
            may_fail=True,
        )
        if shadow_grep_result.return_code != 0 or \
                shadow_grep_result.stdout.strip() != self.line_shadow:
            return ItemStatus(correct=False)

        # verify content of /etc/group
        if not set(self.attributes['groups']) == \
                set(_groups_for_user(self.node, self.name)):
            return ItemStatus(correct=False)

        return ItemStatus(correct=True)


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
