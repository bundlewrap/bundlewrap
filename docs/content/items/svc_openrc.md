# openrc service items

Handles services managed by openrc.

    svc_openrc = {
        "sshd": {
            "enabled": True,  # default
            "running": True,  # default
            "runlevel": "default",  # default
        },
        "nginx": {
            "enabled": False,
            "running": False,
            "runlevel": "boot",
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

## runlevel

Name of the runlevel this service exists in. Defaults to `"default"`.

<hr>

## Canned actions

See also: [Explanation of how canned actions work](../repo/items.py.md#canned-actions)

## reload

Reloads the service. Not all services support reloading.

<hr>

## restart

Restarts the service.

<hr>

## stop

Stops the service.
