# pip package items

Handles Python packages installed by `pip`. Note that you can use the [pip_command node attribute](../repo/nodes.py.md#pip_command) to use `pip3`.

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

<br><br>

# Attribute reference

See also: [The list of generic builtin item attributes](../repo/items.py.md#builtin-item-attributes)

<hr>

## break\_system\_packages

`True` if you want BundleWrap to add the `--break-system-packages` flag. Refer to <https://www.debian.org/releases/bookworm/amd64/release-notes/ch-information.en.html#python3-pep-668>.

Default is `False`.

This feature is *temporary* and usage is *discouraged*. It might be removed from future BundleWrap versions.

<hr>

## installed

`True` when the package is expected to be present on the system; `False` if it should be removed.

<hr>

## version

Force the given exact version to be installed. You can only specify a single version here, selectors like `>=1.0` are NOT supported.

If it's not given, the latest version will be installed initially, but (like the other package items) upgrades will NOT be installed.
