from shlex import quote

from bundlewrap.exceptions import BundleError
from bundlewrap.items import Item
from bundlewrap.utils.text import mark_for_translation as _


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

    def _query(self, sql):
        result = self.run(f'mariadb -Bsr --execute {quote(sql)}')
        return result.stdout.decode().strip()

    def cdict(self):
        if self.attributes['delete']:
            return None
        else:
            return {}

    def fix(self, status):
        if status.must_be_deleted:
            self._query(f"DROP DATABASE `{self.name}`;")
        elif status.must_be_created:
            self._query(f"CREATE DATABASE `{self.name}`;")

    def sdict(self):
        databases = self._query("SHOW DATABASES;").splitlines()
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

