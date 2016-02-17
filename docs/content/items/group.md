# Group items

Manages system groups. Group members are managed through the [user item](user.md).

    groups = {
        "acme": {
            "gid": 2342,
        },
    }

<br>

## Attribute reference

See also: [The list of generic builtin item attributes](../repo/bundles.md#builtin-item-attributes)

<br>

### delete

When set to `True`, this group will be removed from the system. When using `delete`, no other attributes are allowed.

<br>

### gid

Numerical ID of the group.
