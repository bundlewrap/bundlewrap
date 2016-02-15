# Postgres database items

Manages Postgres databases.

    postgres_dbs = {
        "mydatabase": {
            "owner": "me",
        },
    }

<br>

## Attribute reference

See also: [The list of generic builtin item attributes](../repo/bundles.md#builtin-item-attributes)

<br>

### owner

Name of the role which owns this database (defaults to `"postgres"`).
