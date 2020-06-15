# TOML nodes and groups

The primary way to define nodes is in [nodes.py](../repo/nodes.py.md). However, BundleWrap also provides a built-in alternative that you can use to define each node in a [TOML](https://github.com/toml-lang/toml) file. Doing this has pros and cons, which is why you can choose which way is best for you.

*Pros*

* One file per node
* Node files are machine-readable and -writeable
* Easier on the eyes for nodes with simple metadata

*Cons*

* Does not support [Fault objects](../api/#bundlewraputilsfault)
* Does not support [atomic()](../repo/groups.py.md#metadata)
* Does not support `None`
* Does not support sets or tuples
* More difficult to read for long, deeply nested metadata

<br>

## Using TOML nodes

First, you have to make sure your `nodes.py` doesn't overwrite your TOML nodes. Check if your `nodes.py` overwrites the `nodes` dict:

    nodes = {  # bad
        "my_node": {...},
    }

TOML nodes will be added to the `nodes.py` context automatically, so change your `nodes.py` to add to them (or just leave the file empty):

    nodes["my_node"] = {  # good
        ...
    }

Now you are all set to create your first TOML node. Create a file called `nodes/nodenamegoeshere.toml`:

    hostname = "tomlnode.example.com"
    bundles = [
        "bundle1",
        "bundle2",
    ]

    [metadata]
    foo = "bar"

    [metadata.baz]
    frob = 47

And that's it. This node will now be added to your other nodes. You may use subdirectories of `nodes/`, but the node name will always just be the filename minus the ".toml" extension.

<br>

## Converting existing nodes

This is an easy one line operation:

    bw debug -n nodenamegoeshere -c "node.toml_save()"

Don't forget to remove the original node though.

<br>

## Editing TOML nodes from Python

BundleWrap uses [tomlkit](https://github.com/sdispater/tomlkit) internally and exposes a `TOMLDocument` instance as `node.toml` for you to modify:

    $ bw debug -n nodenamegoeshere
    >>> node.file_path
    nodes/nodenamegoeshere.toml
    >>> node.toml['bundles'].append("bundle3")
    >>> node.toml_save()

For your convenience, `.toml_set()` is also provided to easily set nested dict values:

    >>> node.toml_set("metadata/foo/bar/baz", 47)
    >>> node.toml_save()

This should make it pretty straightforward to make changes to lots of nodes without the headaches of using `sed` or something of that nature to edit Python code in `nodes.py`.

<br>

## TOML groups

They work exactly the same way as nodes, but have their own `groups/` directory. `.toml`, `.toml_set()` and `toml_save()` are also found on `Group` objects.
