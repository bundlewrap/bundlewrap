# Pamac package items

Handles packages installed by `pacman` (e.g. Arch Linux), with AUR support by switching to `pamac` when package is told to be installed from AUR.

    pkg_pamac = {
        "foopkg": {
            "installed": True,  # default
        },
        "bar": {
            "installed": False,
        },
        "somethingelse": {
            "aur": True,   # installs package from AUR instead of official repos. Defaults to `false`
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

## aur

`True` when the package should be installed from AUR; `False` if package should be installed from official sources. Defaults to `False`.
