# Directory items

    directories = {
        "/path/to/directory": {
            "mode": "0644",
            "owner": "root",
            "group": "root",
        },
    }

## Attribute reference

See also: [The list of generic builtin item attributes](../repo/bundles.md#builtin-item-attributes)

<br>

### group

Name of the group this directory belongs to. Defaults to `None` (don't care about group).

<br>

### mode

Directory mode as returned by `stat -c %a <directory>`. Defaults to `None` (don't care about mode).

<br>

### owner

Username of the directory's owner. Defaults to `None` (don't care about owner).

<br>

### purge

Set this to `True` to remove everything from this directory that is not managed by BundleWrap. Defaults to `False`.
