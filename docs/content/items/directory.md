# Directory items

    directories = {
        "/path/to/directory": {
            "mode": "0755",
            "owner": "root",
            "group": "root",
        },
    }

<br><br>

# Attribute reference

See also: [The list of generic builtin item attributes](../repo/items.py.md#builtin-item-attributes)

<hr>

## group

Name of the group this directory belongs to. Defaults to `'root'`. Set to `None` if you don't want BundleWrap to change whatever is set on the node.

<hr>

## mode

Directory mode as returned by `stat -c %a <directory>`. Defaults to `755`. Set to `None` if you don't want BundleWrap to change whatever is set on the node.

<hr>

## owner

Username of the directory's owner. Defaults to `'root'`. Set to `None` if you don't want BundleWrap to change whatever is set on the node.

<hr>

## purge

Set this to `True` to remove everything from this directory that is not managed by BundleWrap. Defaults to `False`.

<hr>

## pre_purge_command

Command that will get run on the node prior to `purge` removing a file. Use placeholders `{path}` to get the full path or `{file}` to only get the file name of the file that's getting removed.
