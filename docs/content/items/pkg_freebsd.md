# FreeBSD package items

Handles packages installed by `pkg` on FreeBSD systems.

    pkg_freebsd = {
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
    }

<br><br>

# Attribute reference

See also: [The list of generic builtin item attributes](../repo/items.py.md#builtin-item-attributes)

<hr>

## installed

`True` when the package is expected to be present on the system; `False` if it should be purged.

<hr>


## version

Optional version string. Can be used to select one specific version of a package.

Ignored when `installed` is `False`.
