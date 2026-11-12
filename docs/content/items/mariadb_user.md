# MariaDB user items

Manages MariaDB users.

    mariadb_users = {
        "me": {
            "password": "itsamemario",
            "all_privileges": {
                "mydatabase",
            },
        },
    }

Users are always created for any host, i.e. as `'me'@'%'`.

All commands are run as `root` using the `mariadb` command line client, without any credentials. This works out of the box with MariaDB 10.4 and later, where `root@localhost` can authenticate using the `unix_socket` plugin. Older versions are not supported.

<br><br>

# Attribute reference

See also: [The list of generic builtin item attributes](../repo/items.py.md#builtin-item-attributes)

<hr>

## all\_privileges

A set of database names. The user will be granted `ALL PRIVILEGES` on each of these databases. Any `ALL PRIVILEGES` grants on databases not in this set will be revoked. Other grants are left alone.

[mariadb\_db](mariadb_db.md) items for these databases will automatically be added to `needs`.

<hr>

## password

Plaintext password to set for this user (will be hashed for use with the `mysql_native_password` authentication plugin).

<div class="alert alert-warning">Please do not write any passwords into your bundles. This attribute is intended to be used with an external source of passwords and filled dynamically. If you don't have or want such an elaborate setup, specify passwords using the <code>password_hash</code> attribute instead.</div>

<hr>

## password\_hash

As an alternative to `password`, this allows setting the raw hash as it will be stored in MariaDB's internal database. Should start with "*". You can get it using `SELECT PASSWORD('…');`.

<hr>

## delete

`True` if the user should be deleted (defaults to `False`).
