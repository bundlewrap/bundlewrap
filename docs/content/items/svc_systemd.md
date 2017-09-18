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

<br>

## Attribute reference

See also: [The list of generic builtin item attributes](../repo/bundles.md#builtin-item-attributes)

<br>

### enabled

`True` if the service shall be automatically started during system bootup; `False` otherwise. `None` makes BundleWrap ignore this setting.

<br>

### running

`True` if the service is expected to be running on the system; `False` if it should be stopped. `None` makes BundleWrap ignore this setting.

<br>

## Canned actions

See also: [Explanation of how canned actions work](../repo/bundles.md#canned-actions)

### reload

Reloads the service.

<br>

### restart

Restarts the service.
