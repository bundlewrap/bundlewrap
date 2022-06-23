# dconf items

    dconf = {
        "username/path/to/dconf/setting": {
            "value": "some valid settings option",
            "reset": False,
        },
    }

<br><br>

# Attribute reference

See also: [The list of generic builtin item attributes](../repo/items.py.md#builtin-item-attributes)

<hr>

## value

The value you want the setting to be set to. Must be of type str, int, list, set. Sets will get sorted prior to being set on the system.

<hr>

## reset

Resets the setting to its default value.
