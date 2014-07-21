# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from pipes import quote
from string import ascii_lowercase, digits

from passlib.hash import md5_crypt, sha256_crypt, sha512_crypt

from bundlewrap.exceptions import BundleError
from bundlewrap.items import BUILTIN_ITEM_ATTRIBUTES, Item, ItemStatus
from bundlewrap.utils import LOG
from bundlewrap.utils.text import mark_for_translation as _
from bundlewrap.utils.text import bold


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
    group_output = node.run("grep -e ':{}:$' /etc/group".format(gid), may_fail=True)
    if group_output.return_code != 0:
        return None
    else:
        return group_output.stdout.split(":")[0]


def _groups_for_user(node, username):
    """
    Returns the list of group names for the given username on the given
    node.
    """
    groups = node.run("id -Gn {}".format(username)).stdout.strip().split(" ")
    primary_group = node.run("id -gn {}".format(username)).stdout.strip()
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

    def ask(self, status):
        if not status.info['exists']:
            return _("'{}' not found in /etc/passwd").format(self.name)
        elif self.attributes['delete']:
            return _("'{}' found in /etc/passwd. Will be deleted.").format(self.name)

        output = ""
        for key in status.info['needs_fixing']:
            if key in ('groups', 'password'):
                continue
            output += "{} {} → {}\n".format(
                bold(_ATTRIBUTE_NAMES[key]),
                status.info[key],
                self.attributes[key],
            )

        if self.attributes['password_hash'] is not None:
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

        if self.attributes['groups'] is not None:
            groups_should = set(self.attributes['groups'])
            groups_is = set(status.info['groups'])
            missing_groups = sorted(groups_should.difference(groups_is))
            extra_groups = sorted(groups_is.difference(groups_should))

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
                msg = _("{node}:{bundle}:{item}: deleting...")
            else:
                msg = _("{node}:{bundle}:{item}: updating...")
        else:
            msg = _("{node}:{bundle}:{item}: creating...")
        LOG.info(msg.format(bundle=self.bundle.name, item=self.id, node=self.node.name))

        if self.attributes['delete']:
            self.node.run("userdel {}".format(self.name), may_fail=True)
        else:
            command = "useradd " if not status.info['exists'] else "usermod "
            for attr, option in _ATTRIBUTE_OPTIONS.items():
                if attr in status.info['needs_fixing'] and self.attributes[attr] is not None:
                    if attr == 'groups':
                        value = ",".join(self.attributes[attr])
                    else:
                        value = str(self.attributes[attr])
                    command += "{} {} ".format(option, quote(value))
            command += self.name
            self.node.run(command, may_fail=True)

    def get_status(self):
        # verify content of /etc/passwd
        passwd_grep_result = self.node.run(
            "grep -e '^{}:' /etc/passwd".format(self.name),
            may_fail=True,
        )
        if passwd_grep_result.return_code != 0:
            return ItemStatus(
                correct=self.attributes['delete'],
                info={'exists': False, 'needs_fixing': list(_ATTRIBUTE_OPTIONS.keys())},
            )
        elif self.attributes['delete']:
            return ItemStatus(correct=False, info={
                'exists': True,
                'needs_fixing': list(_ATTRIBUTE_OPTIONS.keys()),
            })

        status = ItemStatus(correct=True, info={'exists': True})
        status.info['needs_fixing'] = []

        status.info.update(_parse_passwd_line(passwd_grep_result.stdout))

        if self.attributes['gid'] is not None:
            if self.attributes['gid'].isdigit():
                if int(self.attributes['gid']) != status.info['gid']:
                    status.info['needs_fixing'].append('gid')
            elif _group_name_for_gid(self.node, status.info['gid']) != self.attributes['gid']:
                status.info['needs_fixing'].append('gid')

        for fieldname in ('uid', 'full_name', 'home', 'shell'):
            if self.attributes[fieldname] is None:
                continue
            if status.info[fieldname] != self.attributes[fieldname]:
                status.info['needs_fixing'].append(fieldname)

        if self.attributes['password_hash'] is not None:
            if self.attributes['use_shadow']:
                # verify content of /etc/shadow
                shadow_grep_result = self.node.run(
                    "grep -e '^{}:' /etc/shadow".format(self.name),
                    may_fail=True,
                )
                if shadow_grep_result.return_code != 0:
                    status.info['shadow_hash'] = None
                    status.info['needs_fixing'].append('password')
                else:
                    status.info['shadow_hash'] = shadow_grep_result.stdout.split(":")[1]
                    if status.info['shadow_hash'] != self.attributes['password_hash']:
                        status.info['needs_fixing'].append('password_hash')
            else:
                if status.info['passwd_hash'] != self.attributes['password_hash']:
                    status.info['needs_fixing'].append('password_hash')

        # verify content of /etc/group
        status.info['groups'] = _groups_for_user(self.node, self.name)

        if self.attributes['groups'] is not None and \
                set(self.attributes['groups']) != set(status.info['groups']):
            status.info['needs_fixing'].append('groups')

        if status.info['needs_fixing']:
            status.correct = False

        return status

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
