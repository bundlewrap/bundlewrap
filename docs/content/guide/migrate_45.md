# Migrating from BundleWrap 4.x to 5.x

As per [semver](http://semver.org), BundleWrap 5.0 breaks compatibility with repositories created for BundleWrap 4.x. This document provides a guide on how to upgrade your repositories to BundleWrap 5.x. Please read the entire document before proceeding.

<br>

<hr>

<br>

## Changes that require you to adjust your repo

<br>

### `svc_upstart` items have been removed

[Upstart](https://en.wikipedia.org/wiki/Upstart_(software)) is a discontinued project, so this item type has been removed.

If you are stuck with upstart for some reason, you will have to copy [the last version of `svc_upstart.py`](https://github.com/bundlewrap/bundlewrap/blob/6d485dedbb8798b86e145d3479178e9d4de5df5e/bundlewrap/items/svc_upstart.py) to your repo as a [custom item type](dev_item.md).

<br>

### Hashing now uses sha256

sha1 has been replaced by sha256 in the following places:

-   `content_hash` of `file` items. You must update your item definitions.
-   When hashing file contents on the node, `sha256` or `sha256sum` (depending on the OS) is now used. This program must exist *on the node*.
-   The `bw hash ...` command will print sha256 hashes now.

<br>

### `repo.nodes_matching()` throws `NoSuchTarget`

When expressions don't match anything, the `NoSuchTarget` exception will now be thrown. You will have to catch this exception and decide what to do. Previously, this case was silently ignored.

<br>

### Hooks are called with named arguments

Hooks are called with named arguments now. The names in your function signature must match the ones in [our documentation](../repo/hooks.md).

For example, you can no longer do this:

    def node_apply_start(my_repo, my_node):
        ...

But you must do this instead:

    def node_apply_start(repo, node):
        ...

<br>

### `get_auto_deps()` has been replaced by `get_auto_attrs()`

[Custom items](dev_item.md) could be instructed to auto-discover dependencies. That happened by calling `get_auto_deps()` on them.

`get_auto_deps()` has now been replaced by the more generic `get_auto_attrs()`, which is able to return different kinds of attributes instead of just `needs`.

To migrate existing code, replace this pattern:

    class MyItem(Item):
        def get_auto_deps(self, items):
            # ...
            return [some_item.id, another_item.id]

With this:

    class MyItem(Item):
        def get_auto_attrs(self, items):
            # ...
            return {
                'needs': [some_item.id, another_item.id],
            }

<br>

### bcrypt

The dependency on [passlib](https://passlib.readthedocs.io/en/stable/) has been removed, becase this library is unmaintained.

This affects `user` items and the `as_htpasswd_entry()` method of [Fault objects](api.md#bundlewraputilsfault). Both will use [bcrypt](https://en.wikipedia.org/wiki/Bcrypt) for hashing now, i.e. they look like `$2b$12$riWuF3Oh...`.

The `hash_method` attribute has been removed from `user` items.

Current versions of nginx and Apache, and current Linux distributions as well as FreeBSD and OpenBSD should support the `$2b$` scheme in their shadow files.

If you do rely on the old behavior, you can still set a `user`'s `password_hash` manually. There is no replacement regarding `as_htpasswd_entry()`, you will have to implement your own version of the old crypt algorithms.

<br>

### `node.metadata_get()` has been removed

This method was deprecated. Use `node.metadata.get()` instead.

<br>

### Canned actions inherit tags

[Canned actions](../repo/items.py.md#canned-actions) like `svc_systemd:nginx:restart` now inherit the tags from their "parent" item. This mostly affects two scenarios.

Suppose you have a [custom item type](dev_item.md) for an init system and you define a service like this:

    svc_fancy_init['nginx'] = {
        'tags': {'causes-downtime'},
    }

If your item type supports canned actions like `svc_fancy_init:nginx:restart` (and if that canned action does not depend on `svc_fancy_init:nginx` itself), then running the following command will now skip both `svc_fancy_init:nginx` and the canned action `svc_fancy_init:nginx:restart`:

    $ bw apply mynode -s tag:causes-downtime

Previously, this *only* skipped `svc_fancy_init:nginx`. (This does not affect item types from core BundleWrap, because all their canned actions already explicitly depend on the parent item.)

The second scenario is that the following was previously impossible, because the canned actions did not inherit the `a` tag and thus a dependency loop was created:

    svc_systemd = {
        'test.service': {
            'tags': {'a'},
            'needed_by': {'!tag:a'},
        },
    }

<br>

### `MetadataUnavailable` instead of `KeyError`

[Metadata reactors](../repo/metadata.py.md#reactors) must now throw `MetadataUnavailable` to indicate that metadata is not available. For example in `metadata.py`:

    from bundlewrap.exceptions import MetadataUnavailable

    @metadata_reactor
    def foo(metadata):
        if some_condition:
            raise MetadataUnavailable()

        return {'foo': True}

<br>

### Items: `display_dicts()` → `display_on_fix()`, `keys` is a set

[Custom items](dev_item.md) must be updated:

-   The method `display_dicts()` has been renamed to `display_on_fix()` for consistency.
-   `display_on_fix()`'s third argument, `keys`, is a set now instead of a list.

<br>

### `metadata` objects don't try to be dicts anymore

This has been deprecated for a long time. If you still have dict-style access like this:

    version = metadata['my_program']['version']

Then you must replace it with this, because this is the only public API of these objects now:

    version = metadata.get('my_program/version')

Also, `metadata.items()`, `metadata.keys()`, and `metadata.values()` is gone.

`metadata.get('foo')` now throws `MetadataUnavailable` instead of silently returning `None`. This matches the behavior of other `get()` operations. For example, `metadata.get('foo/var')` has already thrown an exception; only "root" access was different.

<br>

### `cdict`/`sdict` moved to properties `expected_state`/`actual_state`

The terminology `cdict` and `sdict` has been considered confusing. To alleviate this pain, we use `expected_state` and `actual_state` now.

[Custom items](dev_item.md) must be updated:

-   Rename `cdict` to `expected_state`: This describes the desired state of an item.
-   Rename `sdict` to `actual_state`: This describes the actual state of an item on a node.
-   Both these methods need the `@property` decorator now.

<br>

<hr>

<br>

## Behavioral changes

<br>

### Lock identities have changed

If you have locked a node using `bw lock` and have not overridden your identity using `BW_IDENTITY`, then the identity `$your_username@$your_hostname` was used. This has been changed to now include the Git branch name as well (assuming you're using Git): `$your_username@$your_hostname:$git_branch_name`.

The migration path is to remove the old locks using `bw lock remove ...` and put new locks on the nodes using `bw lock add ...`. How *exactly* this needs to be done depends on your use case.

<br>

### `BW_SCP_ARGS` defaults to the empty string

[This environment variable](env.md#bw_scp_args) used to default to the value of `BW_SSH_ARGS` or, if that was unset, to the empty string. `BW_SSH_ARGS` is used when calling the `ssh` binary on your machine, `BW_SCP_ARGS` for the `scp` binary. Since *some* arguments work for both `ssh` and `scp`, you might have gotten away with setting just `BW_SSH_ARGS` (which implicitly also affected `scp`). This will no longer work.

You must now explicitly set `BW_SCP_ARGS`.

<br>

### `bw apply` and `bw verify`: `-s` without matches is an error now

This is an error now:

    $ bw verify hw.switch-foobar -s tag:causes-downtime
    !!! the following selectors for --skip do not match any items: tag:causes-downtime

The intention is to catch typos. For example, `-s tag:causes_downtime` previously went unnoticed and might have unintentionally restarted some services.

This check is done on the entire selection. If you apply a group and *no* node in that group has items that match the selector, then the error is raised.

There is no direct replacement. If you rely on the old behavior, because you regularly apply nodes where the `-s` argument doesn't match anything, then you must remove `-s` in those cases.

<br>

### Harmonized output of `bw items`

The output of `bw items` was harmonized over all subcomannds. Some subcommands that previously generated JSON now default to table output and will need `--json` to switch back to JSON output.

Tables printed to the CLI with only one column are now formatted as flat list without decorators.

Tables printed to the CLI with the format of `BW_TABLE_STYLE=grep` were changed to repeat literal columns for every row of an array for all tables (not just some), this might require changes to your scripts if you parse `bw` command output.

`bw item NODE ITEM --state` is now called `--actual-state` to clarify its function.

<br>

### `bw plot --no-depends-reverse` has been removed

Instead, reverse dependencies are shown with dashed lines.

<br>

### `bw test` always fails if `test_with` fails

When a `test_with` command failed, we previously ignored this *if* its exit code was 126, 127, or 255. This is no longer the case.

<br>

### `bw lock -i $selector`: Verify if `$selector` matches

To prevent typos and accidents, BundleWrap will now verify if these item selectors match anything. If you don't want this, use `--skip-item-verification`.

<br>

### `bw lock add`: Warning when there are locks always uses a pager

`bw lock add` shows a message like `Your lock was added, but the node was already locked by ...`, followed by a list of existing locks. This output is always piped through a pager now.

This can break your scripts, because they might block now, waiting for the pager to quit. Override the environment variable `PAGER` for these calls if you want the old behavior:

    #!/bin/sh

    PAGER=cat bw lock add ...

<br>

<hr>

<br>

## Minor changes

For everything else, please consult the [changelog](https://github.com/bundlewrap/bundlewrap/blob/main/CHANGELOG.md#500).
