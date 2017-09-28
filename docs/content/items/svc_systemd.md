# systemd service items

Handles services managed by systemd.

    svc_systemd = {
        "fcron.service": {
            "enabled": True,  # default
            "running": True,  # default
        },
        "sgopherd.socket": {
            "running": False,
        },
    }

<br><br>

# Attribute reference

See also: [The list of generic builtin item attributes](../repo/items.py.md#builtin-item-attributes)

<hr>

## enabled

`True` if the service shall be automatically started during system bootup; `False` otherwise. `None` makes BundleWrap ignore this setting.

<hr>

## running

`True` if the service is expected to be running on the system; `False` if it should be stopped. `None` makes BundleWrap ignore this setting.

<hr>

## Canned actions

See also: [Explanation of how canned actions work](../repo/items.py.md#canned-actions)

## reload

Reloads the service.

<hr>

## restart

Restarts the service.
