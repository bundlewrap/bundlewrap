# Migrating from BundleWrap 3.x to 4.x

As per [semver](http://semver.org), BundleWrap 4.0 breaks compatibility with repositories created for BundleWrap 3.x. This document provides a guide on how to upgrade your repositories to BundleWrap 4.x. Please read the entire document before proceeding.

<br>

## metadata.py

Metadata processors have been split into defaults and reactors. See [metadata.py](../repo/metadata.py.md) for details.

Generally speaking, metadata processors that returned `DONE, DEFAULTS` can be turned into defaults.

    @metadata_processor
    def foo(metadata):
       return {"bar": 47}

becomes

    defaults = {
        "bar": 47,
    }

Metadata processors that return `OVERWRITE, RUN_ME_AGAIN` or otherwise depend on other metadata need to be turned into reactors:

    @metadata_processor
    def foo(metadata):
        metadata["bar"] = metadata["baz"] + 5
        return metadata, OVERWRITE, RUN_ME_AGAIN

becomes

    @metadata_reactor
    def foo(metadata):
        return {
            "bar": metadata.get("baz") + 5,
        }

<br>

## members_add and members_remove

These must be replaced by other mechanism, such as the newly-available `groups` attribute on individual nodes. Also note that you can now do `bw apply 'lambda:node.metadata["env"] == "prod"'` so you may no longer have a need to create groups based on metadata.

<br>

## Plugins

The plugin system has been removed since it saw barely any use. The most popular plugin, the `git_deploy` item is now built into BundleWrap itself.

    rm plugins.json
    rm items/git_deploy.py

<br>

## Command line argument parsing

Previously, `bw` used a comma-separated syntax to specify targets for certain actions such as `bw apply`. We now use a space separated style:

    bw apply node1,node2

becomes

    bw apply node1 node2

This may appear trivial, but might lead to confusion with people not used to providing multiple multi-value space-separated arguments on the command line.

    bw nodes -a all node1

becomes

    bw nodes -a all -- node1

The `--` is necessary so we can tell when the argument list for `-a` ends. Here is another example:

    bw nodes -a hostname,bundles node1,node2

becomes

    bw nodes -a hostname bundles -- node1 node2

While a little more verbose, this style let's us use proper shell quoting for argument tokens.

<br>

## Minor changes

For everything else, please consult the [changelog](https://github.com/bundlewrap/bundlewrap/blob/master/CHANGELOG.md#400).
