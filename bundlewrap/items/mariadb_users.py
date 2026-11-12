from hashlib import sha1
from re import match

from bundlewrap.exceptions import BundleError
from bundlewrap.items import Item
from bundlewrap.items.mariadb_dbs import quote_identifier, quote_string, run_query
from bundlewrap.utils.text import mark_for_translation as _


def hash_password(plaintext):
    first_hash_interation = sha1()
    first_hash_interation.update(plaintext.encode())

    second_hash_interation = sha1()
    second_hash_interation.update(first_hash_interation.digest())
    return '*' + second_hash_interation.hexdigest().upper()


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

    def _get_all_privileges(self):
        databases = set()
        grants = run_query(self, f"SHOW GRANTS FOR {quote_string(self.name)};")
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
            'password_hash': hash_password(self.attributes['password']),
            'all_privileges': set(self.attributes['all_privileges']),
        }

    def fix(self, status):
        if status.must_be_deleted:
            run_query(self, f"DROP USER {quote_string(self.name)};")
        elif status.must_be_created:
            run_query(self, f"CREATE USER {quote_string(self.name)};")

        if status.must_be_created or 'password_hash' in status.keys_to_fix:
            password_hash = hash_password(self.attributes['password'])
            run_query(self, f"SET PASSWORD FOR {quote_string(self.name)} = {quote_string(password_hash)};")

        if status.must_be_created or 'all_privileges' in status.keys_to_fix:
            old_grants = self._get_all_privileges()
            to_be_removed = old_grants - self.attributes['all_privileges']
            to_be_added = self.attributes['all_privileges'] - old_grants

            for database in to_be_removed:
                run_query(self, f"REVOKE ALL PRIVILEGES ON {quote_identifier(database)}.* FROM {quote_string(self.name)};")
            for database in to_be_added:
                run_query(self, f"GRANT ALL PRIVILEGES ON {quote_identifier(database)}.* TO {quote_string(self.name)};")
            run_query(self, "FLUSH PRIVILEGES;")

    @property
    def actual_state(self):
        user_exists = run_query(self, f"SELECT EXISTS(SELECT 1 FROM mysql.user WHERE User = {quote_string(self.name)}) AS user_exists;") == "1"

        if user_exists:
            password_hash = run_query(self, f"SELECT `Password` FROM `mysql`.`user` WHERE `User` = {quote_string(self.name)};")
            return {
                'password_hash': password_hash,
                'all_privileges': set(self._get_all_privileges()),
            }
        else:
            return None

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
