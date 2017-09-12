# Directory items

    directories = {
        "/path/to/directory": {
            "mode": "0755",
            "owner": "root",
            "group": "root",
        },
    }

## Attribute reference

See also: [The list of generic builtin item attributes](../repo/bundles.md#builtin-item-attributes)

<br>

### group

Name of the group this directory belongs to. Defaults to `'root'`. Set to `None` if you don't want BundleWrap to change whatever is set on the node.

<br>

### mode

Directory mode as returned by `stat -c %a <directory>`. Defaults to `755`. Set to `None` if you don't want BundleWrap to change whatever is set on the node.

<br>

### owner

Username of the directory's owner. Defaults to `'root'`. Set to `None` if you don't want BundleWrap to change whatever is set on the node.

<br>

### purge

Set this to `True` to remove everything from this directory that is not managed by BundleWrap. Defaults to `False`.
