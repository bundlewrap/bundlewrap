from shlex import quote

from bundlewrap.exceptions import BundleError
from bundlewrap.items import Item
from bundlewrap.utils.text import mark_for_translation as _


def quote_identifier(name):
    """
    Quotes a database, table or column name for use in SQL statements.
    """
    return "`" + name.replace("`", "``") + "`"


def quote_string(value):
    """
    Quotes a value for use as a string literal in SQL statements.
    """
    return "'" + value.replace("\\", "\\\\").replace("'", "\\'") + "'"


def run_query(item, sql):
    result = item.run(f'mariadb -Bsr --execute {quote(sql)}')
    return result.stdout.decode().strip()


class MariadbDB(Item):
    """
    A mariadb database.
    """
    BUNDLE_ATTRIBUTE_NAME = "mariadb_dbs"
    ITEM_ATTRIBUTES = {
        'delete': False,
    }
    ITEM_TYPE_NAME = "mariadb_db"

    def __repr__(self):
        return "<MariadbDB name:{} delete:{}>".format(
            self.name,
            self.attributes['delete'],
        )

    @property
    def expected_state(self):
        if self.attributes['delete']:
            return None
        else:
            return {}

    def fix(self, status):
        if status.must_be_deleted:
            run_query(self, f"DROP DATABASE {quote_identifier(self.name)};")
        elif status.must_be_created:
            run_query(self, f"CREATE DATABASE {quote_identifier(self.name)};")

    @property
    def actual_state(self):
        databases = run_query(self, "SHOW DATABASES;").splitlines()
        if self.name not in databases:
            return None
        else:
            return {}

    @classmethod
    def validate_attributes(cls, bundle, item_id, attributes):
        if not isinstance(attributes.get('delete', True), bool):
            raise BundleError(_(
                "expected boolean for 'delete' on {item} in bundle '{bundle}'"
            ).format(
                bundle=bundle.name,
                item=item_id,
            ))
