# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from pipes import quote

from bundlewrap.exceptions import BundleError
from bundlewrap.items import Item, ItemStatus
from bundlewrap.utils.text import bold, red
from bundlewrap.utils.text import mark_for_translation as _


def create_db(node, name, owner):
    return node.run("sudo -u postgres createdb -wO {owner} {name}".format(
        name=name,
        owner=owner,
    ))


def drop_db(node, name):
    return node.run("sudo -u postgres dropdb -w {}".format(quote(name)))


def get_databases(node):
    output = node.run("echo '\\l' | sudo -u postgres psql -Anqt -F '|' | grep '|'").stdout
    result = {}
    for line in output.strip().split("\n"):
        db, owner = line.strip().split("|", 2)[:2]
        result[db] = {
            'owner': owner,
        }
    return result


def set_owner(node, name, owner):
    return node.run(
        "echo 'ALTER DATABASE {name} OWNER TO {owner}' | "
        "sudo -u postgres psql -nqw".format(
            name=name,
            owner=owner,
        ),
    )


class PostgresDB(Item):
    """
    A postgres database.
    """
    BUNDLE_ATTRIBUTE_NAME = "postgres_dbs"
    ITEM_ATTRIBUTES = {
        'delete': False,
        'owner': "postgres",
    }
    ITEM_TYPE_NAME = "postgres_db"
    NEEDS_STATIC = [
        "pkg_apt:",
        "pkg_pacman:",
        "pkg_yum:",
        "pkg_zypper:",
        "postgres_role:",
    ]
    def __repr__(self):
        return "<PostgresDB name:{}>".format(self.name)

    def ask(self, status):
        if not status.info['exists'] and not self.attributes['delete']:
            return _("Doesn't exist. Do you want to create it?")
        if status.info['exists'] and self.attributes['delete']:
            return red(_("Will be deleted."))
        if status.info['owner'] != self.attributes['owner']:
            return "{} {} → {}".format(
                bold(_("owner")),
                status.info['owner'],
                self.attributes['owner'],
            )

    def fix(self, status):
        if 'existence' in status.info['needs_fixing']:
            if self.attributes['delete']:
                drop_db(self.node, self.name)
            else:
                create_db(self.node, self.name, self.attributes['owner'])
        elif 'owner' in status.info['needs_fixing']:
            set_owner(self.node, self.name, self.attributes['owner'])

    def get_status(self):
        databases = get_databases(self.node)
        status_info = {
            'exists': self.name in databases,
            'needs_fixing': [],
        }
        status_info.update(databases[self.name])
        if self.attributes['delete'] == status_info['exists']:
            status_info['needs_fixing'].append('existence')
            return ItemStatus(correct=False, info=status_info)
        elif (
            not self.attributes['delete'] and
            self.attributes['owner'] != databases[self.name]['owner']
        ):
            status_info['needs_fixing'].append('owner')
            return ItemStatus(correct=False, info=status_info)
        return ItemStatus(correct=True, info=status_info)

    @classmethod
    def validate_attributes(cls, bundle, item_id, attributes):
        if not isinstance(attributes.get('delete', True), bool):
            raise BundleError(_(
                "expected boolean for 'delete' on {item} in bundle '{bundle}'"
            ).format(
                bundle=bundle.name,
                item=item_id,
            ))
