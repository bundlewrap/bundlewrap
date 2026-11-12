# MariaDB database items

Manages MariaDB databases.

    mariadb_dbs = {
        "mydatabase": {},
    }

All commands are run as `root` using the `mariadb` command line client, without any credentials. This works out of the box with MariaDB 10.4 and later, where `root@localhost` can authenticate using the `unix_socket` plugin. Older versions are not supported.

<br><br>

# Attribute reference

See also: [The list of generic builtin item attributes](../repo/items.py.md#builtin-item-attributes)

<hr>

## delete

`True` if the database should be deleted (defaults to `False`).
