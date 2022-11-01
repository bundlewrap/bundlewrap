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

<div class="alert alert-info">Due to how <code>dconf</code> works, it is currenty required to have a running <code>dbus</code> session when this item is changed. The easiest way to achive this is by logging in to this user in the GUI.</div>

<hr>

## value

The value you want the setting to be set to. Must be of type str, int, list, set. Sets will get sorted prior to being set on the system.

<hr>

## reset

If set to `True`, resets the setting to its default value. If set, `value` will get ignored.
