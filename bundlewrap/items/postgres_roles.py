from passlib.apps import postgres_context
from shlex import quote

from bundlewrap.exceptions import BundleError
from bundlewrap.items import Item
from bundlewrap.utils.text import force_text, mark_for_translation as _


AUTHID_COLUMNS = {
    "rolcanlogin": 'can_login',
    "rolsuper": 'superuser',
    "rolpassword": 'password_hash',
}


def delete_role(node, role):
    node.run("dropuser -w {}".format(role), user="postgres")


def fix_role(node, role, attrs, create=False):
    if create:
        superuser_sql = "SUPERUSER" if attrs['superuser'] else "NOSUPERUSER"
        create_sql = f'CREATE ROLE "{role}" WITH LOGIN {superuser_sql}'
        node.run(f"psql -nqw -c {quote(create_sql)}", user="postgres")
    else:
        superuser_sql = "SUPERUSER" if attrs['superuser'] else "NOSUPERUSER"
        alter_superuser_sql = f'ALTER ROLE "{role}" {superuser_sql}'
        node.run(f"psql -nqw -c {quote(alter_superuser_sql)}", user="postgres")

    password_sql = f"UPDATE pg_authid SET rolpassword = '{attrs['password_hash']}' WHERE rolname = '{role}'"
    node.run(f"psql -nqw -c {quote(password_sql)}", user="postgres")


def get_role(node, role):
    sql = f"SELECT rolcanlogin, rolsuper, rolpassword from pg_authid WHERE rolname='{role}'"
    result = node.run(f"psql -Anqwx -F '|' -c \"{sql}\"", user="postgres")

    role_attrs = {}
    for line in force_text(result.stdout).strip().split("\n"):
        try:
            key, value = line.split("|")
        except ValueError:
            pass
        else:
            role_attrs[AUTHID_COLUMNS[key]] = value

    for bool_attr in ('can_login', 'superuser'):
        if bool_attr in role_attrs:
            role_attrs[bool_attr] = role_attrs[bool_attr] == "t"

    return role_attrs if role_attrs else None


class PostgresRole(Item):
    """
    A postgres role.
    """
    BUNDLE_ATTRIBUTE_NAME = "postgres_roles"
    ITEM_ATTRIBUTES = {
        'can_login': True,
        'delete': False,
        'password': None,
        'password_hash': None,
        'superuser': False,
    }
    ITEM_TYPE_NAME = "postgres_role"

    def __repr__(self):
        return "<PostgresRole name:{} superuser:{} delete:{}>".format(
            self.name,
            self.attributes['superuser'],
            self.attributes['delete'],
        )

    def cdict(self):
        if self.attributes['delete']:
            return None
        cdict = self.attributes.copy()
        del cdict['delete']
        del cdict['password']
        return cdict

    def fix(self, status):
        if status.must_be_deleted:
            delete_role(self.node, self.name)
        elif status.must_be_created:
            fix_role(self.node, self.name, self.attributes, create=True)
        else:
            fix_role(self.node, self.name, self.attributes)

    def sdict(self):
        return get_role(self.node, self.name)

    def patch_attributes(self, attributes):
        if 'password' in attributes:
            attributes['password_hash'] = postgres_context.encrypt(
                force_text(attributes['password']),
                user=self.name,
            )
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
