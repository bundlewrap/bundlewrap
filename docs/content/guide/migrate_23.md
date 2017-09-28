# Migrating from BundleWrap 2.x to 3.x

As per [semver](http://semver.org), BundleWrap 3.0 breaks compatibility with repositories created for BundleWrap 2.x. This document provides a guide on how to upgrade your repositories to BundleWrap 3.x. Please read the entire document before proceeding.

<br>

## metadata.py

BundleWrap 2.x simply used all functions in `metadata.py` whose names don't start with an underscore as metadata processors. This led to awkward imports like `from foo import bar as _bar`. BundleWrap 3.x requires a decorator for explicitly designating functions as metadata processors:

	@metadata_processor
	def myproc(metadata):
	    return metadata, DONE

You will have to add `@metadata_processor` to each metadata processor function. There is no need to import it; it is provided automatically, just like `node` and `repo`.

The accepted return values of metadata processors have changed as well. Metadata processors now always have to return a tuple with the first element being a dictionary of metadata and the remaining elements made up of various options to tell BundleWrap what to do with the dictionary. In most cases, you will want to return the `DONE` options as in the example above. There is no need to import options, they're always available.

When you previously returned `metadata, False` from a metadata processor, you will now have to return `metadata, RUN_ME_AGAIN`. For a more detailed description of the available options, see [the documentation](../repo/metadata.py.md).

<br>

## File and directory ownership defaults

[Files](../items/file.md), [directories](../items/directory.md), and [symlinks](../items/symlink.md) now have default values for the ownership and mode attributes. Previously the default was to ignore them. It's very likely that you won't have to do anything here, just be aware.

<br>

## systemd services enabled by default

Again, just be [aware](../items/svc_systemd.md), it's probably what you intended anyway.

<br>

## Environment variables

The following [env vars](env.md) have been renamed (though the new names have already been available for a while, so chances are you're already using them):

<table>
<tr><th>Old</th><th>New</th></tr>
<tr><td><code>BWADDHOSTKEYS</code></td><td><code>BW_ADD_HOST_KEYS</code></td></tr>
<tr><td><code>BWCOLORS</code></td><td><code>BW_COLORS</code></td></tr>
<tr><td><code>BWITEMWORKERS</code></td><td><code>BW_ITEM_WORKERS</code></td></tr>
<tr><td><code>BWNODEWORKERS</code></td><td><code>BW_NODE_WORKERS</code></td></tr>
</table>

<br>

## Item.display_keys and Item.display_dicts

If you've written your own items and used the `display_keys()` or `display_dicts()` methods or the `BLOCK_CONCURRENT` attribute, you will have to update them to the [new API](dev_item.md).
