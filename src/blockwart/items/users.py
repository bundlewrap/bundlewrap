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
        if passwd_grep_result.return_code != 0:
            return ItemStatus(correct=False, info={'exists': False})

        status = ItemStatus(correct=True, info={'exists': True})
        status.info.update(_parse_passwd_line(passwd_grep_result.stdout))

        if passwd_grep_result.stdout.strip() != self.line_passwd:
            status.correct = False

        # verify content of /etc/shadow
        shadow_grep_result = self.node.run(
            "grep -e '^{}:' /etc/shadow".format(self.name),
            may_fail=True,
        )
        if shadow_grep_result.return_code != 0:
            status.correct = False
            status.info['password'] = None
        else:
            status.info['password'] = shadow_grep_result.stdout.split(":")[1]
            if status.info['password'] != self.attributes['password']:
                status.correct = False

        # verify content of /etc/group
        status.info['groups'] = _groups_for_user(self.node, self.name)
        if set(self.attributes['groups']) != set(status.info['groups']):
            status.correct = False

        return status


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
