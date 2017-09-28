# Upstart service items

Handles services managed by Upstart.

    svc_upstart = {
        "gunicorn": {
            "running": True,  # default
        },
        "celery": {
            "running": False,
        },
    }

<br>

# Attribute reference

See also: [The list of generic builtin item attributes](../repo/bundles.md#builtin-item-attributes)

<br>

## running

`True` if the service is expected to be running on the system; `False` if it should be stopped.

<br>

## Canned actions

See also: [Explanation of how canned actions work](../repo/bundles.md#canned-actions)

## reload

Reloads the service.

<br>

## restart

Restarts the service.

<br>

## stopstart

Stops and then starts the service. This is different from `restart` in that Upstart will pick up changes to the `/etc/init/SERVICENAME.conf` file, while `restart` will continue to use the version of that file that the service was originally started with. See [http://askubuntu.com/a/238069](http://askubuntu.com/a/238069).
