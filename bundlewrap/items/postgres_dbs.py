# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from pipes import quote

from bundlewrap.exceptions import BundleError
from bundlewrap.items import Item
from bundlewrap.utils.text import force_text, mark_for_translation as _


def create_db(node, name, attributes):
    template = None
    cmd = "sudo -u postgres createdb -wO {} ".format(attributes['owner'])

    if attributes.get('collation') is not None:
        cmd += "--lc-collate={} ".format(attributes['collation'])
        template = "template0"

    if attributes.get('ctype') is not None:
        cmd += "--lc-ctype={} ".format(attributes['ctype'])
        template = "template0"

    if attributes.get('encoding') is not None:
        cmd += "--encoding={} ".format(attributes['encoding'])
        template = "template0"

    if template is not None:
        cmd += "--template={} ".format(template)

    cmd += name

    return node.run(cmd)


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
        'collation': None,  # creation-time only
        'ctype': None,      # creation-time only
        'encoding': None,   # creation-time only
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
        if status.must_be_deleted:
            drop_db(self.node, self.name)
        elif status.must_be_created:
            create_db(self.node, self.name, self.attributes)
        elif 'owner' in status.keys_to_fix:
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
