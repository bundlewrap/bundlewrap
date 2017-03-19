# APT package items

Handles packages installed by `apt-get` on Debian-based systems.

    pkg_apt = {
        "foopkg": {
            "installed": True,  # default
        },
        "bar": {
            "installed": False,
        },
        "awesome-daemon": {
            "start_service": False,
        },
    }

<br>

## Attribute reference

See also: [The list of generic builtin item attributes](../repo/bundles.md#builtin-item-attributes)

<br>

### installed

`True` when the package is expected to be present on the system; `False` if it should be purged.

### start\_service

By default, daemons will be auto-started on systems like Debian or Ubuntu. This happens right after the package has been installed. You might want to set `start_service` to `False` to avoid this. This might be necessary if BundleWrap must place some more config files on the node before a daemon can actually be started.
