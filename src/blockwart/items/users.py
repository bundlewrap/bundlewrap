# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from pipes import quote
from string import ascii_lowercase, digits

from passlib.hash import md5_crypt, sha256_crypt, sha512_crypt

from blockwart.exceptions import BundleError
from blockwart.items import Item, ItemStatus
from blockwart.utils import LOG
from blockwart.utils.text import mark_for_translation as _
from blockwart.utils.text import bold


_ATTRIBUTE_NAMES = {
    'full_name': _("full name"),
    'gid': _("GID"),
    'groups': _("groups"),
    'home': _("home dir"),
    'password_hash': _("password hash"),
    'shell': _("shell"),
    'uid': _("UID"),
}

# a random static salt if users don't provide one
_DEFAULT_SALT = "uJzJlYdG"

HASH_METHODS = {
    'md5': md5_crypt,
    'sha256': sha256_crypt,
    'sha512': sha512_crypt,
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
        ('username', 'passwd_hash', 'uid', 'gid', 'gecos', 'home', 'shell'),
        line.strip().split(":"),
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
    DEPENDS_STATIC = ["group:"]
    ITEM_ATTRIBUTES = {
        'delete': False,
        'full_name': "",
        'gid': None,
        'groups': [],
        'hash_method': 'sha512',
        'home': None,
        'password': None,
        'password_hash': "!",
        'salt': None,
        'shell': "/bin/bash",
        'uid': None,
        'use_shadow': None,
    }
    ITEM_TYPE_NAME = "user"

    def __repr__(self):
        return "<User name:{} uid:{} gid:{} home:{} shell:{} groups:{}>".format(
            self.name,
            self.attributes['uid'],
            self.attributes['gid'],
            self.attributes['home'],
            self.attributes['shell'],
            ",".join(self.attributes['groups']),
        )

    def ask(self, status):
        if not status.info['exists']:
            return _("'{}' not found in /etc/passwd").format(self.name)
        elif self.attributes['delete']:
            return _("'{}' found in /etc/passwd. Will be deleted.").format(self.name)

        output = ""
        for key, should_value in self.attributes.iteritems():
            if key in ('delete', 'groups', 'hash_method', 'password', 'password_hash',
                       'salt', 'use_shadow'):
                continue
            is_value = status.info[key]
            if should_value != is_value:
                output += "{} {} → {}\n".format(
                    bold(_ATTRIBUTE_NAMES[key]),
                    is_value,
                    should_value,
                )

        if self.attributes['use_shadow']:
            filename = "/etc/shadow"
            found_hash = status.info['shadow_hash']
        else:
            filename = "/etc/passwd"
            found_hash = status.info['passwd_hash']

        if found_hash is None:
            output += bold(_ATTRIBUTE_NAMES['password_hash']) + " " + \
                      _("not found in {}").format(filename) + "\n"
        elif found_hash != self.attributes['password_hash']:
            output += bold(_ATTRIBUTE_NAMES['password_hash']) + " " + \
                      found_hash + "\n"
            output += " " * (len(_ATTRIBUTE_NAMES['password_hash']) - 1) + "→ " + \
                      self.attributes['password_hash'] + "\n"

        groups_should = set(self.attributes['groups'])
        groups_is = set(status.info['groups'])
        missing_groups = list(groups_should.difference(groups_is))
        missing_groups.sort()
        extra_groups = list(groups_is.difference(groups_should))
        extra_groups.sort()

        if missing_groups:
            output += bold(_("missing groups")) + " " + \
                      ", ".join(missing_groups) + "\n"

        if extra_groups:
            output += bold(_("extra groups")) + " " + \
                      ", ".join(extra_groups) + "\n"

        return output

    def fix(self, status):
        if status.info['exists']:
            if self.attributes['delete']:
                msg = _("{}:{}: deleting...")
            else:
                msg = _("{}:{}: updating...")
        else:
            msg = _("{}:{}: creating...")
        LOG.info(msg.format(self.node.name, self.id))

        if self.attributes['delete']:
            self.node.run("userdel {}".format(self.name))
        else:
            self.node.run("{command} "
                "-d {home} "
                "-g {gid} "
                "-G {groups} "
                "-p {password_hash} "
                "-s {shell} "
                "-u {uid} "
                "{username}".format(
                    command="useradd" if not status.info['exists'] else "usermod",
                    home=quote(self.attributes['home']),
                    gid=self.attributes['gid'],
                    groups=quote(",".join(self.attributes['groups'])),
                    password_hash=quote(self.attributes['password_hash']),
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
            return ItemStatus(
                correct=self.attributes['delete'],
                info={'exists': False},
            )
        elif self.attributes['delete']:
            return ItemStatus(correct=False, info={'exists': True})

        status = ItemStatus(correct=True, info={'exists': True})
        status.info.update(_parse_passwd_line(passwd_grep_result.stdout))

        if passwd_grep_result.stdout.strip() != self.line_passwd:
            status.correct = False

        if self.attributes['use_shadow']:
            # verify content of /etc/shadow
            shadow_grep_result = self.node.run(
                "grep -e '^{}:' /etc/shadow".format(self.name),
                may_fail=True,
            )
            if shadow_grep_result.return_code != 0:
                status.correct = False
                status.info['shadow_hash'] = None
            else:
                status.info['shadow_hash'] = shadow_grep_result.stdout.split(":")[1]
                if status.info['shadow_hash'] != self.attributes['password_hash']:
                    status.correct = False
        else:
            if status.info['passwd_hash'] != self.attributes['password_hash']:
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
            'x' if self.attributes['use_shadow'] else self.attributes['password_hash'],
            str(self.attributes['uid']),
            str(self.attributes['gid']),
            self.attributes['full_name'],
            self.attributes['home'],
            self.attributes['shell'],
        ])

    def patch_attributes(self, attributes):
        if 'home' not in attributes:
            attributes['home'] = "/home/{}".format(self.name)

        if attributes.get('password', None) is not None and \
                not 'password_hash' in attributes:
            # defaults aren't set yet
            hash_method = HASH_METHODS[attributes.get(
                'hash_method',
                self.ITEM_ATTRIBUTES['hash_method'],
            )]
            attributes['password_hash'] = hash_method.encrypt(
                attributes['password'],
                rounds=5000,  # default from glibc
                salt=attributes.get('salt', _DEFAULT_SALT),
            )

        if 'use_shadow' not in attributes:
            attributes['use_shadow'] = self.node.use_shadow_passwords

        return attributes

    def validate_attributes(self, attributes):
        if attributes.get('delete', False) and len(attributes.keys()) > 1:
            raise BundleError(_(
                "{} from bundle '{}' cannot have other attributes besides 'delete'"
            ).format(self.id, self.bundle.name))
        elif not attributes.get('delete', False) and not (
            'gid' in attributes or
            'groups' in attributes or
            'uid' in attributes
        ):
            raise BundleError(_(
                "{} from bundle '{}' must define gid, groups and uid"
            ).format(self.id, self.bundle.name))

        if 'hash_method' in attributes and \
                attributes['hash_method'] not in HASH_METHODS:
            raise BundleError(
                _("Invalid hash method for {}: '{}'").format(
                    self.id,
                    attributes['hash_method'],
                )
            )

        if 'password_hash' in attributes and (
            'password' in attributes or
            'salt' in attributes
        ):
            raise BundleError(
                _("{}: 'password_hash' cannot be used "
                  "with 'password' or 'salt'").format(self.id)
            )

        if 'salt' in attributes and 'password' not in attributes:
            raise BundleError(
                _("{}: salt given without a password").format(self.id)
            )

        if not attributes.get('delete', False) and \
                'password' not in attributes and \
                'password_hash' not in attributes:
            raise BundleError(_("{} needs to specify either "
                                "a password or a password hash").format(self.id))

    @classmethod
    def validate_name(cls, bundle, name):
        for char in name:
            if char not in _USERNAME_VALID_CHARACTERS:
                raise BundleError(_(
                    "Invalid character in username '{}': {} (bundle '{}')"
                ).format(name, char, bundle.name))

        if name.endswith("_") or name.endswith("-"):
            raise BundleError(_(
                "Username '{}' must not end in dash or underscore (bundle '{}')"
            ).format(name, bundle.name))

        if len(name) > 30:
            raise BundleError(_(
                "Username '{}' is longer than 30 characters (bundle '{}')"
            ).format(name, bundle.name))
