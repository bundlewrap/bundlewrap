# Postgres role items

Manages Postgres roles.

    postgres_roles = {
        "me": {
            "superuser": True,
            "password": "itsamemario",
        },
    }

<br>

## Attribute reference

See also: [The list of generic builtin item attributes](../repo/bundles.md#builtin-item-attributes)

<br>

### superuser

`True` if the role should be given superuser privileges (defaults to `False`).

<br>

### password

Plaintext password to set for this role (will be hashed using MD5).

<div class="alert alert-warning">Please do not write any passwords into your bundles. This attribute is intended to be used with an external source of passwords and filled dynamically. If you don't have or want such an elaborate setup, specify passwords using the <code>password_hash</code> attribute instead.</div>

<br>

### password_hash

As an alternative to `password`, this allows setting the raw hash as it will be stored in Postgres' internal database. Should start with "md5".
