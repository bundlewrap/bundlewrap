# Postgres database items

Manages Postgres databases.

    postgres_dbs = {
        "mydatabase": {
            "owner": "me",
            "when_creating": {
                "encoding": "LATIN1",
                "collation": "de_DE.ISO-8859-1",
                "ctype": "de_DE.ISO-8859-1",
            },
        },
    }

<br><br>

# Attribute reference

See also: [The list of generic builtin item attributes](../repo/items.py.md#builtin-item-attributes)

<hr>

## owner

Name of the role which owns this database (defaults to `"postgres"`).

<hr>

## when\_creating

### encoding, collation, and ctype

By default, BundleWrap will only create a database using your default PostgreSQL template, which most likely is `template1`. This means it will use the same encoding and collation that `template1` uses. By specifying any of the attributes `encoding`, `collation`, or `ctype`, BundleWrap will instead create a new database from `template0`, thus allowing you to override said database attributes.

These options are creation-time only.
