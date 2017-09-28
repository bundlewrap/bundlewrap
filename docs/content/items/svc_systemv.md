# System V service items

Handles services managed by traditional System V init scripts.

    svc_systemv = {
        "apache2": {
            "running": True,  # default
        },
        "mysql": {
            "running": False,
        },
    }

<br><br>

# Attribute reference

See also: [The list of generic builtin item attributes](../repo/items.py.md#builtin-item-attributes)

<hr>

## running

`True` if the service is expected to be running on the system; `False` if it should be stopped.

<hr>

## Canned actions

See also: [Explanation of how canned actions work](../repo/items.py.md#canned-actions)

## reload

Reloads the service.

<hr>

## restart

Restarts the service.
