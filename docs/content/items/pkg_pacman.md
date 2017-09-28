# Pacman package items

Handles packages installed by `pacman` (e.g. Arch Linux).

    pkg_pacman = {
        "foopkg": {
            "installed": True,  # default
        },
        "bar": {
            "installed": False,
        },
        "somethingelse": {
            "tarball": "something-1.0.pkg.tar.gz",
        }
    }

<div class="alert alert-warning">System updates on Arch Linux should <strong>always</strong> be performed manually and with great care. Thus, this item type installs packages with a simple <code>pacman -S $pkgname</code> instead of the commonly recommended <code>pacman -Syu $pkgname</code>. You should <strong>manually</strong> do a full system update before installing new packages via BundleWrap!</div>

<br><br>

# Attribute reference

See also: [The list of generic builtin item attributes](../repo/items.py.md#builtin-item-attributes)

<hr>

## installed

`True` when the package is expected to be present on the system; `False` if this package and all dependencies that are no longer needed should be removed.

<hr>

## tarball

Upload a local file to the node and install it using `pacman -U`. The value of `tarball` must point to a file relative to the `pkg_pacman` subdirectory of the current bundle.
