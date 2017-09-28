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

<hr>

## stopstart

Stops and then starts the service. This is different from `restart` in that Upstart will pick up changes to the `/etc/init/SERVICENAME.conf` file, while `restart` will continue to use the version of that file that the service was originally started with. See [http://askubuntu.com/a/238069](http://askubuntu.com/a/238069).
