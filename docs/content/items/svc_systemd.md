# systemd service items

Handles services managed by systemd.

    svc_systemd = {
        "fcron.service": {
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

### running

`True` if the service is expected to be running on the system; `False` if it should be stopped.

<br>

## Canned actions

See also: [Explanation of how canned actions work](../repo/bundles.md#canned-actions)

### reload

Reloads the service.

<br>

### restart

Restarts the service.
