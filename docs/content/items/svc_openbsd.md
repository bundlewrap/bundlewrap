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

<br><br>

# Attribute reference

See also: [The list of generic builtin item attributes](../repo/items.py.md#builtin-item-attributes)

<hr>

## enabled

`True` if the service shall be automatically started during system bootup; `False` otherwise. `True`, the default value, is needed on OpenBSD, as starting disabled services fails.

<hr>

## running

`True` if the service is expected to be running on the system; `False` if it should be stopped.

<hr>

## Canned actions

See also: [Explanation of how canned actions work](../repo/items.py.md#canned-actions)

## restart

Restarts the service.

<hr>

## stopstart

Stops and starts the service.
