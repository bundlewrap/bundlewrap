# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from logging import ERROR, getLogger
from pipes import quote
from string import ascii_lowercase, digits

from passlib.hash import bcrypt, md5_crypt, sha256_crypt, sha512_crypt

from bundlewrap.exceptions import BundleError
from bundlewrap.items import BUILTIN_ITEM_ATTRIBUTES, Item
from bundlewrap.utils.text import force_text, mark_for_translation as _


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

# bcrypt needs special salts. 22 characters long, ending in ".", "O", "e", "u"
# see https://bitbucket.org/ecollins/passlib/issues/25
_DEFAULT_BCRYPT_SALT = "oo2ahgheen9Tei0IeJohTO"

HASH_METHODS = {
    'md5': md5_crypt,
    'sha256': sha256_crypt,
    'sha512': sha512_crypt,
    'bcrypt': bcrypt
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


def _parse_passwd_line(line, entries):
    """
    Parses a line from /etc/passwd and returns the information as a
    dictionary.
    """

    result = dict(zip(
        entries,
        line.strip().split(":"),
    ))
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

    def __repr__(self):
        return "<User name:{}>".format(self.name)

    def cdict(self):
        if self.attributes['delete']:
            return None
        cdict = self.attributes.copy()
        del cdict['delete']
        del cdict['hash_method']
        del cdict['password']
        del cdict['salt']
        del cdict['use_shadow']
        for key in list(cdict.keys()):
            if cdict[key] is None:
                del cdict[key]
        if 'groups' in cdict:
            cdict['groups'] = set(cdict['groups'])
        return cdict

    def fix(self, status):
        if status.must_be_deleted:
            self.node.run("userdel {}".format(self.name), may_fail=True)
        else:
            command = "useradd " if status.must_be_created else "usermod "
            for attr, option in sorted(_ATTRIBUTE_OPTIONS.items()):
                if (attr in status.keys_to_fix or status.must_be_created) and \
                        self.attributes[attr] is not None:
                    if attr == 'groups':
                        value = ",".join(self.attributes[attr])
                    else:
                        value = str(self.attributes[attr])
                    command += "{} {} ".format(option, quote(value))
            command += self.name
            self.node.run(command, may_fail=True)

    def get_auto_deps(self, items):
        deps = []
        for item in items:
            if item.ITEM_TYPE_NAME == "group":
                if item.attributes['delete']:
                    raise BundleError(_(
                        "{item1} (from bundle '{bundle1}') depends on item "
                        "{item2} (from bundle '{bundle2}') which is set to be deleted"
                    ).format(
                        item1=self.id,
                        bundle1=self.bundle.name,
                        item2=item.id,
                        bundle2=item.bundle.name,
                    ))
                else:
                    deps.append(item.id)
        return deps

    def sdict(self):
        # verify content of /etc/passwd
        if self.node.os in self.node.OS_FAMILY_BSD:
            password_command = "grep -ae '^{}:' /etc/master.passwd"
        else:
            password_command = "grep -ae '^{}:' /etc/passwd"
        passwd_grep_result = self.node.run(
            password_command.format(self.name),
            may_fail=True,
        )
        if passwd_grep_result.return_code != 0:
            return None

        if self.node.os in self.node.OS_FAMILY_BSD:
            entries = (
                'username',
                'passwd_hash',
                'uid',
                'gid',
                'class',
                'change',
                'expire',
                'gecos',
                'home',
                'shell',
            )
        else:
            entries = ('username', 'passwd_hash', 'uid', 'gid', 'gecos', 'home', 'shell')

        sdict = _parse_passwd_line(passwd_grep_result.stdout_text, entries)

        if self.attributes['gid'] is not None and not self.attributes['gid'].isdigit():
            sdict['gid'] = _group_name_for_gid(self.node, sdict['gid'])

        if self.attributes['password_hash'] is not None:
            if self.attributes['use_shadow'] and self.node.os not in self.node.OS_FAMILY_BSD:
                # verify content of /etc/shadow unless we are on OpenBSD
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
            if self.node.os in self.node.OS_FAMILY_BSD:
                attributes['password_hash'] = bcrypt.encrypt(
                    force_text(attributes['password']),
                    rounds=8,  # default rounds for OpenBSD accounts
                    salt=_DEFAULT_BCRYPT_SALT if salt is None else salt,
                )
            else:
                attributes['password_hash'] = hash_method.encrypt(
                    force_text(attributes['password']),
                    rounds=5000,  # default from glibc
                    salt=_DEFAULT_SALT if salt is None else salt,
                )

        if 'use_shadow' not in attributes:
            attributes['use_shadow'] = self.node.use_shadow_passwords

        for attr in ('gid', 'uid'):
            if isinstance(attributes.get(attr), int):
                attributes[attr] = str(attributes[attr])

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
