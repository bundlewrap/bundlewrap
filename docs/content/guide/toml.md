# TOML nodes and groups

The primary way to define nodes is in [nodes.py](../repo/nodes.py.md). However, BundleWrap also provides a built-in alternative that you can use to define each node in a [TOML](https://github.com/toml-lang/toml) file. Doing this has pros and cons, which is why you can choose which way is best for you.

*Pros*

* One file per node
* Node files are machine-readable and -writeable
* Easier on the eyes for nodes with simple metadata

*Cons*

* Does not support [Fault objects](api.md#bundlewraputilsfault)
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

<br>

## Using secrets

Due to TOML nodes and groups not supporting python code, BundleWrap supports what we call "magic strings".
These allow you to use secrets in your nodes with just using a special syntax inside a string.

To define magic strings, you need to add a `magic_strings.py` to your repository. It might look like
this example:

```python
# `vault`, `libs` and `repo_path` are available for your convenience

@magic_string
def decrypt(string):
    return vault.decrypt(string)
```

In your node you then use the function as follows, where
`encrypt$gAAAAABo90x3H...` is the result of `bw pw -e "foo"`:

```toml
mysecret = "!decrypt:encrypt$gAAAAABo90x3H..."
```

The part between `!` and `:` is used as the function name, everything after the `:` will be passed
as argument to the called function (this may be an empty string, e.g. `"!none:"`). Bundlewrap will
raise `InvalidMagicStringException` if the function cannot be found.

Names must match `[a-zA-Z0-9_]+` and be unique. They default to the function name; pass `name=` to
the decorator for names that are not valid Python identifiers:

```python
@magic_string(name="32_random_bytes_as_base64_for")
def random_bytes(identifier):
    return vault.random_bytes_as_base64_for(identifier)
```

### Node-specific secrets

For magic strings in nodes (not groups), BundleWrap passes the node to your function if the
function's signature has a `node` parameter. Combine this with
[`node.vault`](secrets.md#nodevault-per-node-and-per-group-keys) to use the node's own keys:

```python
@magic_string
def password_for(identifier, node=None):
    # `node` is None for magic strings in groups
    return (node.vault if node else vault).password_for(identifier)
```

The node is still being loaded at this point. `node.name` and the lazy `node.vault` functions
(`password_for()`, `human_password_for()`, `random_bytes_as_base64_for()`, `decrypt()`,
`decrypt_file()`, `decrypt_file_as_base64()`, `cmd()`) are safe to use; `node.vault.encrypt()` and
`encrypt_file()` are not lazy and cannot be used here. Reading node attributes such as
`node.generate_key` or `node.os` raises an error, `node.metadata` fails because the node is not
registered yet, and `node.groups` must not be used because it would be cached from the unconverted
attributes.

### `atomic()` in TOML

Using this mechanism, you could also use `atomic()` in TOML nodes and groups
by creating a magic string which will return an atomic result:

```python
from ast import literal_eval
from bundlewrap.metadata import atomic as _bw_atomic

@magic_string
def atomic(arg):
    # Using `literal_eval()` here will prevent you from most accidents
    # by only allowing strings, bytes, numbers, tuples, lists, dicts,
    # sets, booleans, `None` and `Ellipsis`
    # https://docs.python.org/3/library/ast.html#ast.literal_eval
    return _bw_atomic(literal_eval(arg))
```

So, to create an atomic list, you'd put a python list into a magic string like
this:

```toml
something_atomic = "!atomic:['a list', 'which is', 'atomic']"
```
