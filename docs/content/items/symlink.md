# Symlink items

    symlinks = {
        "/some/symlink": {
            "group": "root",
            "owner": "root",
            "target": "/target/file",
        },
    }

<br>

# Attribute reference

See also: [The list of generic builtin item attributes](../repo/bundles.md#builtin-item-attributes)

<br>

## target

File or directory this symlink points to. **This attribute is required.**

<br>

## group

Name of the group this symlink belongs to. Defaults to `'root'`. Set to `None` if you don't want BundleWrap to change whatever is set on the node.

<br>

## owner

Username of the symlink's owner. Defaults to `'root'`. Set to `None` if you don't want BundleWrap to change whatever is set on the node.
