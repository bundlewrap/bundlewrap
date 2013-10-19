# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from pipes import quote
from string import ascii_lowercase, digits

from blockwart.exceptions import BundleError
from blockwart.items import Item, ItemStatus
from blockwart.utils.text import mark_for_translation as _
from blockwart.utils.text import white


_ATTRIBUTE_NAMES = {
    'full_name': _("full name"),
    'gid': _("GID"),
    'groups': _("groups"),
    'home': _("home dir"),
    'password': _("password"),
    'shell': _("shell"),
    'uid': _("UID"),
}

_USERNAME_VALID_CHARACTERS = ascii_lowercase + digits + "-_"

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
    REQUIRED_ATTRIBUTES = ['gid', 'groups', 'uid']

    def ask(self, status):
        if not status.info['exists']:
            return _("'{}' not found in /etc/passwd").format(self.name)

        output = ""
        for key, should_value in self.attributes.iteritems():
            if key in ('groups', 'password'):
                continue
            is_value = status.info[key]
            if should_value != is_value:
                output += "{} {} → {}\n".format(
                    white(_ATTRIBUTE_NAMES[key], bold=True),
                    is_value,
                    should_value,
                )

        if status.info['password'] is None:
            output += white(_ATTRIBUTE_NAMES['password'], bold=True) + " " + \
                      _("not found in /etc/shadow") + "\n"
        elif status.info['password'] != self.attributes['password']:
            output += white(_ATTRIBUTE_NAMES['password'], bold=True) + " " + \
                      status.info['password'] + "\n"
            output += " " * (len(_ATTRIBUTE_NAMES['password']) - 1) + "→ " + \
                      self.attributes['password'] + "\n"

        groups_should = set(self.attributes['groups'])
        groups_is = set(status.info['groups'])
        missing_groups = list(groups_should.difference(groups_is))
        missing_groups.sort()
        extra_groups = list(groups_is.difference(groups_should))
        extra_groups.sort()

        if missing_groups:
            output += white(_("missing groups"), bold=True) + " " + \
                      ", ".join(missing_groups) + "\n"

        if extra_groups:
            output += white(_("extra groups"), bold=True) + " " + \
                      ", ".join(extra_groups) + "\n"

        return output

    def fix(self, status):
        if not status.info['exists']:
            self.node.run("useradd {}".format(self.name))

        self.node.run("usermod "
            "-d {home} "
            "-g {gid} "
            "-G {groups} "
            "-p {password} "
            "-s {shell} "
            "-u {uid} "
            "{username}".format(
                home=quote(self.attributes['home']),
                gid=self.attributes['gid'],
                groups=quote(",".join(self.attributes['groups'])),
                password=quote(self.attributes['password']),
                shell=quote(self.attributes['shell']),
                uid=self.attributes['uid'],
                username=self.name,
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

    @classmethod
    def validate_name(cls, name):
        for char in name:
            if char not in _USERNAME_VALID_CHARACTERS:
                raise BundleError(
                    _("Invalid character in username '{}': {}").format(name, char)
                )

        if name.endswith("_") or name.endswith("-"):
            raise BundleError(
                _("Username '{}' must not end in dash or underscore")
            )

        if len(name) > 30:
            raise BundleError(
                _("Username '{}' is longer than 30 characters")
            )
