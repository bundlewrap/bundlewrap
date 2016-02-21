# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from pipes import quote

from bundlewrap.exceptions import BundleError
from bundlewrap.items import Item
from bundlewrap.utils.text import force_text, mark_for_translation as _


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
    for line in force_text(output).strip().split("\n"):
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

    def __repr__(self):
        return "<PostgresDB name:{}>".format(self.name)

    def cdict(self):
        if self.attributes['delete']:
            return None
        else:
            return {'owner': self.attributes['owner']}

    def fix(self, status):
        if not status.cdict:
            drop_db(self.node, self.name)
        elif not status.sdict:
            create_db(self.node, self.name, self.attributes['owner'])
        elif 'owner' in status.keys:
            set_owner(self.node, self.name, self.attributes['owner'])
        else:
            raise AssertionError("this shouldn't happen")

    def get_auto_deps(self, items):
        deps = []
        for item in items:
            if item.ITEM_TYPE_NAME == "postgres_role" and item.name == self.attributes['owner']:
                deps.append(item.id)
        return deps

    def sdict(self):
        databases = get_databases(self.node)
        if self.name not in databases:
            return None
        else:
            return {'owner': databases[self.name]['owner']}

    @classmethod
    def validate_attributes(cls, bundle, item_id, attributes):
        if not isinstance(attributes.get('delete', True), bool):
            raise BundleError(_(
                "expected boolean for 'delete' on {item} in bundle '{bundle}'"
            ).format(
                bundle=bundle.name,
                item=item_id,
            ))
