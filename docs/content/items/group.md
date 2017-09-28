# Group items

Manages system groups. Group members are managed through the [user item](user.md).

    groups = {
        "acme": {
            "gid": 2342,
        },
    }

<br><br>

# Attribute reference

See also: [The list of generic builtin item attributes](../repo/items.py.md#builtin-item-attributes)

<hr>

## delete

When set to `True`, this group will be removed from the system. When using `delete`, no other attributes are allowed.

<hr>

## gid

Numerical ID of the group.
