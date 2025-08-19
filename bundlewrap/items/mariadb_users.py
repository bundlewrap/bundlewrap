from hashlib import sha1
from re import match as re_match
from shlex import quote

from bundlewrap.exceptions import BundleError
from bundlewrap.items import Item
from bundlewrap.utils.text import mark_for_translation as _


def hash_password(plaintext):
    m = sha1()
    m.update(plaintext)

    n = sha1()
    n.update(m.digest())
    return '*' + n.hexdigest().upper()


class MariadbUser(Item):
    """
    A mariadb user.
    """
    BUNDLE_ATTRIBUTE_NAME = "mariadb_users"
    ITEM_ATTRIBUTES = {
        'delete': False,
        'password': None,
        'all_privileges': set(),
    }
    ITEM_TYPE_NAME = "mariadb_user"

    def __repr__(self):
        return "<MariadbUser name:{} delete:{} password_hash:{} all_privileges:{}>".format(
            self.name,
            self.attributes['delete'],
            hash_password(self.attributes['password']),
            sorted(self.attributes['all_privileges']),
        )

    def _query(self, sql):
        result = self.run(f'mariadb -Bsr --execute {quote(sql)}')
        return result.stdout.decode().strip()

    def _get_all_privileges(self):
        databases = set()
        grants = self._query(f"SHOW GRANTS FOR `{self.name}`;")
        for grant in grants.splitlines():
            if not grant.startswith("GRANT ALL PRIVILEGES ON "):
                continue

            m = re_match(r'ON `(.+)`\.', grant)
            if not m:
                continue

            databases.add(m.groups()[1])
        return databases

    def cdict(self):
        if self.attributes['delete']:
            return None
        return {
            'password_hash': hash_password(self.attributes['password']),
            'all_privileges': set(self.attributes['all_privileges']),
        }

    def fix(self, status):
        if status.must_be_deleted:
            self._query(f"DROP USER '{self.name}';")
        elif status.must_be_created:
            self._query(f"CREATE USER '{self.name}';")

        if status.must_be_created or 'password_hash' in status.keys_to_fix:
            self._query(f"SET PASSWORD FOR '{self.name}' = '{quote(self.attributes['password'])}';")

        if status.must_be_created or 'all_privileges' in status.keys_to_fix:
            old_grants = self._get_all_privileges()
            to_be_removed = old_grants - self.attributes['all_privileges']
            to_be_added = self.attributes['all_privileges'] - old_grants

            for i in to_be_removed:
                self._query(f"REVOKE ALL PRIVILEGES ON `{i}`.* FROM '{self.name}';")
            for i in to_be_added:
                self._query(f"GRANT ALL PRIVILEGES ON `{i}`.* TO '{self.name}';")
            self._query("FLUSH PRIVILEGES;")

    def sdict(self):
        password_hash = self._query(f"SELECT `Password` FROM `mysql`.`user` WHERE `User` = '{self.name}';")
        if not password_hash:
            return None
        return {
            'password_hash': password_hash,
            'all_privileges': set(self._get_all_privileges()),
        }

    def get_auto_attrs(self, items):
        needs = set()
        for item in items:
            if item.ITEM_TYPE_NAME == "mariadb_db" and item.name in self.attributes['all_privileges']:
                needs.add(item.id)
        return {
            'needs': needs,
        }

    @classmethod
    def validate_attributes(cls, bundle, item_id, attributes):
        if not attributes.get('delete', False):
            if attributes.get('password') is None:
                raise BundleError(_(
                    "expected 'password' on {item} in bundle '{bundle}'"
                ).format(
                    bundle=bundle.name,
                    item=item_id,
                ))
        if not isinstance(attributes.get('delete', True), bool):
            raise BundleError(_(
                "expected boolean for 'delete' on {item} in bundle '{bundle}'"
            ).format(
                bundle=bundle.name,
                item=item_id,
            ))
