# pip package items

Handles Python packages installed by `pip`.

    pkg_pip = {
        "foo": {
            "installed": True,  # default
            "version": "1.0",  # optional
        },
        "bar": {
            "installed": False,
        },
        "/path/to/virtualenv/foo": {
        	# will install foo in the virtualenv at /path/to/virtualenv
        },
    }

<br>

# Attribute reference

See also: [The list of generic builtin item attributes](../repo/bundles.md#builtin-item-attributes)

<br>

## installed

`True` when the package is expected to be present on the system; `False` if it should be removed.

<br>

## version

Force the given exact version to be installed. You can only specify a single version here, selectors like `>=1.0` are NOT supported.

If it's not given, the latest version will be installed initially, but (like the other package items) upgrades will NOT be installed.
