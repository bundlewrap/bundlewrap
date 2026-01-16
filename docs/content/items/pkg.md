# Package management items

BundleWrap ensures that no two bundles defines the same item – every item definition must be unique and unambiguous. For most items this is totally fine – we rarely want to define the same file from multiple bundles, but for package management items this can become frustrating.

Imagine the following case:

```python
# bundles/foo/items.py

pkg_apt['postgresql'] = {}
```

```python
# bundles/bar/items.py

pkg_apt['postgresql'] = {}
```

```python
# nodes.py
nodes['mynode'] = {
    'hostname': "localhost",
    'bundles': {
        'foo',
        'bar',
    }
}
```

This example will fail:

```none
$ bw test mynode
✓ No reactors violated their declared keys
✓ mynode  has no metadata conflicts
Traceback (most recent call last):
  …

bundlewrap.exceptions.BundleError: duplicate definition of pkg_apt:postgresql in bundles 'foo' and 'bar'
```

To solve this conundrum, BundleWrap strongly suggest to use a package manager bundle to resolve these conflicts in a way that suites your use case. A very simple solution might look like this (similar for package managers other than `apt`):

```python
# bundles/apt/items.py
for pkg, conf in node.metadata.get('apt/packages', {}).items():
    pkg_apt[pkg] = conf
```

```python
# bundles/foo/metadata.py

defaults = {
    'apt': {
        'packages': {
            'postgresql': {},
        },
    },
}
```

```python
# bundles/bar/metadata.py

defaults = {
    'apt': {
        'packages': {
            'postgresql': {},
        },
    },
}
```

```python
# nodes.py
nodes['mynode'] = {
    'hostname': "localhost",
    'bundles': {
        'apt',
        'foo',
        'bar',
    }
}
```

Now, the conflict resolution is handled by the metadata dict, which will warn when metadata clashes between bundles (in case of atomic data types), but now you are free to implement whichever resolution algorithm you want in your package management bundle: The example above only uses Python dicts, which get merged automatically by BundleWrap.

Usually, the `apt` bundle would be added to the nodes via a [group](group.md) so that it does not need to be added manually to every node.
