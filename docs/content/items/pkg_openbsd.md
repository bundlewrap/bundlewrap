# OpenBSD package items

Handles packages installed by `pkg_add` on OpenBSD systems.

    pkg_openbsd = {
        "foo": {
            "installed": True,  # default
        },
        "bar": {
            "installed": True,
            "version": "1.0",
        },
        "baz": {
            "installed": False,
        },
        "qux": {
            "flavor": "no_x11",
        },
    }

<br><br>

# Attribute reference

See also: [The list of generic builtin item attributes](../repo/items.py.md#builtin-item-attributes)

<hr>

## installed

`True` when the package is expected to be present on the system; `False` if it should be purged.

<hr>

## flavor

Optional, defaults to the "normal" flavor.

Ignored when `version` is set or when `installed` is `False`.

<hr>

## version

Optional version string. Can be used to select one specific version of a package, including its flavor. For example, set this to `1.0.4p0-socks` for the package `irssi` to run `pkg_add irssi-1.0.4p0-socks`.

Ignored when `flavor` is set or when `installed` is `False`.
