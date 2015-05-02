# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from passlib.apps import postgres_context

from bundlewrap.exceptions import BundleError
from bundlewrap.items import Item, ItemStatus
from bundlewrap.utils.text import bold, red
from bundlewrap.utils.text import mark_for_translation as _


AUTHID_COLUMNS = {
    "rolsuper": 'superuser',
    "rolpassword": 'password_hash',
}

ATTRS = {
    'password_hash': _("password hash"),
    'superuser': _("superuser"),
}


def delete_role(node, role):
    node.run("sudo -u postgres dropuser -w {}".format(role))


def fix_role(node, role, attrs, create=False):
    password = " PASSWORD '{}'".format(attrs['password_hash'])
    node.run(
        "echo \"{operation} ROLE '{role}' WITH {superuser}SUPERUSER{password}\" "
        "| sudo -u postgres psql -nqw".format(
            operation="CREATE" if create else "ALTER",
            password="" if attrs['password_hash'] is None else password,
            role=role,
            superuser="" if attrs['superuser'] is True else "NO",
        )
    )


def get_role(node, role):
    result = node.run("echo \"SELECT rolsuper, rolpassword from pg_authid WHERE rolname='{}'\" "
                      "| sudo -u postgres psql -Anqwx -F '|'".format(role))

    role_attrs = {}
    for line in result.stdout.strip().split("\n"):
        try:
            key, value = line.split("|")
        except ValueError:
            pass
        else:
            role_attrs[AUTHID_COLUMNS[key]] = value

    role_attrs['superuser'] = role_attrs['superuser'] == "t"

    return role_attrs


class PostgresRole(Item):
    """
    A postgres role.
    """
    BUNDLE_ATTRIBUTE_NAME = "postgres_roles"
    ITEM_ATTRIBUTES = {
        'delete': False,
        'password': None,
        'password_hash': None,
        'superuser': False,
    }
    ITEM_TYPE_NAME = "postgres_role"

    def __repr__(self):
        return "<PostgresRole name:{}>".format(self.name)

    def ask(self, status):
        if not status.info['exists'] and not self.attributes['delete']:
            return _("Doesn't exist. Do you want to create it?")
        if status.info['exists'] and self.attributes['delete']:
            return red(_("Will be deleted."))
        output = []
        for attr, attr_pretty in ATTRS.items():
            if status.info[attr] != self.attributes[attr]:
                return "{} {} → {}".format(
                    bold(attr_pretty),
                    status.info[attr],
                    self.attributes[attr],
                )
        return "\n".join(output)

    def fix(self, status):
        if 'existence' in status.info['needs_fixing']:
            if self.attributes['delete']:
                delete_role(self.node, self.name)
            else:
                fix_role(self.node, self.name, self.attributes, create=True)
        else:
            fix_role(self.node, self.name, self.attributes)

    def get_status(self):
        role_attrs = get_role(self.name, self.name)
        status_info = {
            'exists': bool(role_attrs),
            'needs_fixing': [],
        }

        if self.attributes['delete'] == status_info['exists']:
            status_info['needs_fixing'].append('existence')

        if not self.attributes['delete'] and status_info['exists']:
            for attr in ATTRS.keys():
                if self.attributes[attr] is not None and self.attributes[attr] != role_attrs[attr]:
                    status_info['needs_fixing'].append(attr)

        return ItemStatus(correct=not bool(status_info['needs_fixing']), info=status_info)

    def patch_attributes(self, attributes):
        if 'password' in attributes:
            attributes['password_hash'] = postgres_context.encrypt(
                attributes['password'],
                user=self.name,
            )
        return attributes

    @classmethod
    def validate_attributes(cls, bundle, item_id, attributes):
        if not isinstance(attributes.get('delete', True), bool):
            raise BundleError(_(
                "expected boolean for 'delete' on {item} in bundle '{bundle}'"
            ).format(
                bundle=bundle.name,
                item=item_id,
            ))
