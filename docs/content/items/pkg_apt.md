# APT package items

Handles packages installed by `apt-get` on Debian-based systems.

    pkg_apt = {
        "foopkg": {
            "installed": True,  # default
        },
        "bar_i386": {  # i386 multiarch variant of the "bar" package
            "installed": False,
        },
        "awesome-daemon": {
            "when_creating": {
                "start_service": False,
            },
        },
    }

<br><br>

# Attribute reference

See also: [The list of generic builtin item attributes](../repo/items.py.md#builtin-item-attributes)

<hr>

## installed

`True` when the package is expected to be present on the system; `False` if it should be purged.

<hr>

## when\_creating

These attributes are only enforced during the creation of the item on the node (in this case this means when a package is installed). They are ignored in subsequent runs of `bw apply`.

<hr>

### start\_service

By default, daemons will be auto-started on systems like Debian or Ubuntu. This happens right after the package has been installed. You might want to set `start_service` to `False` to avoid this. This might be necessary if BundleWrap must place some more config files on the node before a daemon can actually be started.
