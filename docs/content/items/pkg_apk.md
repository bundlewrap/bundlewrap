# apk package items

Handles packages installed by `apk` on Alpine Linux.

    pkg_apk = {
        "foopkg": {
            "installed": True,  # default
        },
        "bar": {
            "installed": False,
        },
    }

<br>

## Attribute reference

See also: [The list of generic builtin item attributes](../repo/bundles.md#builtin-item-attributes)

<br>

### installed

`True` when the package is expected to be present on the system; `False` if it should be removed.
