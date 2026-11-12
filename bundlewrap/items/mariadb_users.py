from hashlib import sha1
from re import match

from bundlewrap.exceptions import BundleError
from bundlewrap.items import Item
from bundlewrap.items.mariadb_dbs import quote_identifier, quote_string, run_query
from bundlewrap.utils.text import force_text, mark_for_translation as _


def hash_password(plaintext):
    """
    Returns the hash MariaDB's mysql_native_password plugin would store
    for the given password (equivalent to `SELECT PASSWORD(…)`).
    """
    first_hash_iteration = sha1()
    first_hash_iteration.update(force_text(plaintext).encode('UTF-8'))

    second_hash_iteration = sha1()
    second_hash_iteration.update(first_hash_iteration.digest())
    return '*' + second_hash_iteration.hexdigest().upper()


def parse_all_privileges_grant(grant):
    """
    Given a line of `SHOW GRANTS` output, returns the name of the database
    if it grants ALL PRIVILEGES on that database, otherwise None.
    """
    result = match(r"GRANT ALL PRIVILEGES ON `((?:[^`]|``)+)`\.\* TO ", grant)
    if not result:
        return None
    return result.group(1).replace("``", "`")


class MariadbUser(Item):
    """
    A mariadb user.
    """
    BUNDLE_ATTRIBUTE_NAME = "mariadb_users"
    ITEM_ATTRIBUTES = {
        'delete': False,
        'password': None,
        'password_hash': None,
        'all_privileges': set(),
    }
    ITEM_TYPE_NAME = "mariadb_user"

    def __repr__(self):
        return "<MariadbUser name:{} delete:{} all_privileges:{}>".format(
            self.name,
            self.attributes['delete'],
            sorted(self.attributes['all_privileges']),
        )

    @property
    def _account(self):
        return f"{quote_string(self.name)}@'%'"

    def _get_all_privileges(self):
        databases = set()
        grants = run_query(self, f"SHOW GRANTS FOR {self._account};")
        for grant in grants.splitlines():
            database = parse_all_privileges_grant(grant)
            if database is not None:
                databases.add(database)
        return databases

    @property
    def expected_state(self):
        if self.attributes['delete']:
            return None
        return {
            'password_hash': self.attributes['password_hash'],
            'all_privileges': self.attributes['all_privileges'],
        }

    def fix(self, status):
        if status.must_be_deleted:
            run_query(self, f"DROP USER {self._account};")
            return
        elif status.must_be_created:
            run_query(self, f"CREATE USER {self._account};")

        if status.must_be_created or 'password_hash' in status.keys_to_fix:
            run_query(
                self,
                f"ALTER USER {self._account} IDENTIFIED VIA mysql_native_password "
                f"USING {quote_string(self.attributes['password_hash'])};",
            )

        if status.must_be_created or 'all_privileges' in status.keys_to_fix:
            old_grants = self._get_all_privileges()
            to_be_removed = old_grants - self.attributes['all_privileges']
            to_be_added = self.attributes['all_privileges'] - old_grants

            for database in to_be_removed:
                run_query(self, f"REVOKE ALL PRIVILEGES ON {quote_identifier(database)}.* FROM {self._account};")
            for database in to_be_added:
                run_query(self, f"GRANT ALL PRIVILEGES ON {quote_identifier(database)}.* TO {self._account};")

    @property
    def actual_state(self):
        result = run_query(
            self,
            f"SELECT 1, authentication_string FROM mysql.user "
            f"WHERE User = {quote_string(self.name)} AND Host = '%';",
        )
        if not result:
            return None

        password_hash = result.split("\t", 1)[1] if "\t" in result else ""
        return {
            'password_hash': password_hash,
            'all_privileges': self._get_all_privileges(),
        }

    def get_auto_attrs(self, items):
        needs = set()
        for item in items:
            if item.ITEM_TYPE_NAME == "mariadb_db" and item.name in self.attributes['all_privileges']:
                needs.add(item.id)
        return {
            'needs': needs,
        }

    def patch_attributes(self, attributes):
        if attributes.get('password') is not None:
            attributes['password_hash'] = hash_password(attributes['password'])
        return attributes

    @classmethod
    def validate_attributes(cls, bundle, item_id, attributes):
        if not attributes.get('delete', False):
            if attributes.get('password') is None and attributes.get('password_hash') is None:
                raise BundleError(_(
                    "expected either 'password' or 'password_hash' on {item} in bundle '{bundle}'"
                ).format(
                    bundle=bundle.name,
                    item=item_id,
                ))
        if attributes.get('password') is not None and attributes.get('password_hash') is not None:
            raise BundleError(_(
                "can't define both 'password' and 'password_hash' on {item} in bundle '{bundle}'"
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
