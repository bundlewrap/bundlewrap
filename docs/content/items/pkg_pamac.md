# Pamac package items

Handles packages installed by `pacman` (e.g. Arch Linux) and `pamac`. Uses `pamac` to install, build and remove packages. Needs `pacman` to determine if a package is installed.
`Pacman` is only used to read information from the node, all action is handeled by `pamac`.

    pkg_pamac = {
        "foopkg": {
            "installed": True,  # default
        },
        "bar": {
            "installed": False,
        },
        "somethingelse": {
			"when_creating": {
	            "aur": True,   # installs package from AUR instead of official repos. Defaults to `False`
			},
        }.
    }

<div class="alert alert-warning">System updates on Arch Linux should <strong>always</strong> be performed manually and with great care. Thus, this item type installs packages with <code>pamac install --no-upgrade $pkgname</code>. You should <strong>manually</strong> do a full system update before installing new packages via BundleWrap!</div>

<br><br>

# Attribute reference

See also: [The list of generic builtin item attributes](../repo/items.py.md#builtin-item-attributes)

<hr>

## installed

`True` when the package is expected to be present on the system; `False` if this package and all dependencies that are no longer needed should be removed.

<hr>

## aur

`True` when the package should be installed from AUR; `False` if package should be installed from official sources. Defaults to `False`.  
This attribute will only be read when creating the item on the node, e.g. when the desired package will be installed for the first time. In subsequent runs, this item will be ignored. See [when\_creating documentation](../repo/items.py.md#when_creating)
