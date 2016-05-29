# OpenBSD service items

Handles services on OpenBSD.

    svc_openbsd = {
        "bgpd": {
            "enabled": True, # default
            "running": True,  # default
        },
        "supervisord": {
            "running": False,
        },
    }

<br>

## Attribute reference

See also: [The list of generic builtin item attributes](../repo/bundles.md#builtin-item-attributes)

<br>

### enabled

`True` if the service shall be automatically started during system bootup; `False` otherwise. `True`, the default value, is needed on OpenBSD, as starting disabled services fails.

<br>

### running

`True` if the service is expected to be running on the system; `False` if it should be stopped.

<br>

## Canned actions

See also: [Explanation of how canned actions work](../repo/bundles.md#canned-actions)

### restart

Restarts the service.

<br>

### stopstart

Stops and starts the service.
