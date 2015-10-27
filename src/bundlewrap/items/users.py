# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from logging import ERROR, getLogger
from pipes import quote
from string import ascii_lowercase, digits

from passlib.hash import md5_crypt, sha256_crypt, sha512_crypt

from bundlewrap.exceptions import BundleError
from bundlewrap.items import BUILTIN_ITEM_ATTRIBUTES, Item, ItemStatus
from bundlewrap.utils.text import mark_for_translation as _
from bundlewrap.utils.text import bold
from bundlewrap.utils.ui import io


getLogger('passlib').setLevel(ERROR)

_ATTRIBUTE_NAMES = {
    'full_name': _("full name"),
    'gid': _("GID"),
    'groups': _("groups"),
    'home': _("home dir"),
    'password_hash': _("password hash"),
    'shell': _("shell"),
    'uid': _("UID"),
}

_ATTRIBUTE_OPTIONS = {
    'full_name': "-c",
    'gid': "-g",
    'groups': "-G",
    'home': "-d",
    'password_hash': "-p",
    'shell': "-s",
    'uid': "-u",
}

# a random static salt if users don't provide one
_DEFAULT_SALT = "uJzJlYdG"

HASH_METHODS = {
    'md5': md5_crypt,
    'sha256': sha256_crypt,
    'sha512': sha512_crypt,
}

_USERNAME_VALID_CHARACTERS = ascii_lowercase + digits + "-_"


def _group_name_for_gid(node, gid):
    """
    Returns the group name that matches the gid.
    """
    group_output = node.run("grep -e ':{}:[^:]*$' /etc/group".format(gid), may_fail=True)
    if group_output.return_code != 0:
        return None
    else:
        return group_output.stdout_text.split(":")[0]


def _groups_for_user(node, username):
    """
    Returns the list of group names for the given username on the given
    node.
    """
    groups = node.run("id -Gn {}".format(username)).stdout_text.strip().split(" ")
    primary_group = node.run("id -gn {}".format(username)).stdout_text.strip()
    groups.remove(primary_group)
    return groups


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
    ITEM_ATTRIBUTES = {
        'delete': False,
        'full_name': None,
        'gid': None,
        'groups': None,
        'hash_method': 'sha512',
        'home': None,
        'password': None,
        'password_hash': None,
        'salt': None,
        'shell': None,
        'uid': None,
        'use_shadow': None,
    }
    ITEM_TYPE_NAME = "user"
    NEEDS_STATIC = ["group:"]

    def __repr__(self):
        return "<User name:{}>".format(self.name)

    def cdict(self):
        if self.attributes['delete']:
            return {}
        cdict = self.attributes.copy()
        cdict['groups'] = set(cdict['groups'])
        del cdict['delete']
        del cdict['hash_method']
        del cdict['password']
        del cdict['salt']
        del cdict['use_shadow']
        return cdict

    def fix(self, status):
        if not status.cdict:
            self.node.run("userdel {}".format(self.name), may_fail=True)
        else:
            command = "useradd " if not status.sdict else "usermod "
            for attr, option in sorted(_ATTRIBUTE_OPTIONS.items()):
                if attr in status.keys and self.attributes[attr] is not None:
                    if attr == 'groups':
                        value = ",".join(self.attributes[attr])
                    else:
                        value = str(self.attributes[attr])
                    command += "{} {} ".format(option, quote(value))
            command += self.name
            self.node.run(command, may_fail=True)

    def sdict(self):
        # verify content of /etc/passwd
        passwd_grep_result = self.node.run(
            "grep -e '^{}:' /etc/passwd".format(self.name),
            may_fail=True,
        )
        if passwd_grep_result.return_code != 0:
            return {}

        sdict = _parse_passwd_line(passwd_grep_result.stdout_text)

        if self.attributes['gid'] is not None and not self.attributes['gid'].isdigit():
            sdict['gid'] = _group_name_for_gid(self.node, sdict['gid'])

        if self.attributes['password_hash'] is not None:
            if self.attributes['use_shadow']:
                # verify content of /etc/shadow
                shadow_grep_result = self.node.run(
                    "grep -e '^{}:' /etc/shadow".format(self.name),
                    may_fail=True,
                )
                if shadow_grep_result.return_code != 0:
                    sdict['password_hash'] = None
                else:
                    sdict['password_hash'] = shadow_grep_result.stdout_text.split(":")[1]
            else:
                sdict['password_hash'] = sdict['passwd_hash']
        del sdict['passwd_hash']

        # verify content of /etc/group
        sdict['groups'] = set(_groups_for_user(self.node, self.name))

        return sdict

    def patch_attributes(self, attributes):
        if attributes.get('password', None) is not None:
            # defaults aren't set yet
            hash_method = HASH_METHODS[attributes.get(
                'hash_method',
                self.ITEM_ATTRIBUTES['hash_method'],
            )]
            salt = attributes.get('salt', None)
            attributes['password_hash'] = hash_method.encrypt(
                attributes['password'],
                rounds=5000,  # default from glibc
                salt=_DEFAULT_SALT if salt is None else salt,
            )

        if 'use_shadow' not in attributes:
            attributes['use_shadow'] = self.node.use_shadow_passwords

        if attributes.get('gid', None) is not None:
            attributes['gid'] = str(attributes['gid'])

        return attributes

    @classmethod
    def validate_attributes(cls, bundle, item_id, attributes):
        if attributes.get('delete', False):
            for attr in attributes.keys():
                if attr not in ['delete'] + list(BUILTIN_ITEM_ATTRIBUTES.keys()):
                    raise BundleError(_(
                        "{item} from bundle '{bundle}' cannot have other "
                        "attributes besides 'delete'"
                    ).format(item=item_id, bundle=bundle.name))

        if 'hash_method' in attributes and \
                attributes['hash_method'] not in HASH_METHODS:
            raise BundleError(
                _("Invalid hash method for {item} in bundle '{bundle}': '{method}'").format(
                    bundle=bundle.name,
                    item=item_id,
                    method=attributes['hash_method'],
                )
            )

        if 'password_hash' in attributes and (
            'password' in attributes or
            'salt' in attributes
        ):
            raise BundleError(_(
                "{item} in bundle '{bundle}': 'password_hash' "
                "cannot be used with 'password' or 'salt'"
            ).format(bundle=bundle.name, item=item_id))

        if 'salt' in attributes and 'password' not in attributes:
            raise BundleError(
                _("{}: salt given without a password").format(item_id)
            )

    @classmethod
    def validate_name(cls, bundle, name):
        for char in name:
            if char not in _USERNAME_VALID_CHARACTERS:
                raise BundleError(_(
                    "Invalid character in username '{user}': {char} (bundle '{bundle}')"
                ).format(bundle=bundle.name, char=char, user=name))

        if name.endswith("_") or name.endswith("-"):
            raise BundleError(_(
                "Username '{user}' must not end in dash or underscore (bundle '{bundle}')"
            ).format(bundle=bundle.name, user=name))

        if len(name) > 30:
            raise BundleError(_(
                "Username '{user}' is longer than 30 characters (bundle '{bundle}')"
            ).format(bundle=bundle.name, user=name))
