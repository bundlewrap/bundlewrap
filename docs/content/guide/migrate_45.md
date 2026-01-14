# Migrating from BundleWrap 4.x to 5.x

As per [semver](http://semver.org), BundleWrap 5.0 breaks compatibility with repositories created for BundleWrap 4.x. This document provides a guide on how to upgrade your repositories to BundleWrap 5.x. Please read the entire document before proceeding.

<br>

## Lock identities have changed

If you have locked a node using `bw lock` and have not overridden your identity using `BW_IDENTITY`, then the identity `$your_username@$your_hostname` was used. This has been changed to now include the Git branch name as well (assuming you're using Git): `$your_username@$your_hostname:$git_branch_name`.

The migration path is to remove the old locks using `bw lock remove ...` and put new locks on the nodes using `bw lock add ...`. How *exactly* this needs to be done depends on your use case.

No changes to the repository are required.

<br>

## `svc_upstart` items have been removed

[Upstart](https://en.wikipedia.org/wiki/Upstart_(software)) is a discontinued project, so this item type has been removed.

If you are stuck with upstart for some reason, you will have to copy [the last version of `svc_upstart.py`](https://github.com/bundlewrap/bundlewrap/blob/6d485dedbb8798b86e145d3479178e9d4de5df5e/bundlewrap/items/svc_upstart.py) to your repo as a [custom item type](dev_item.md).

<br>

## Hashing now uses sha256

sha1 has been replaced by sha256 in the following places:

-   `content_hash` of `file` items. You must update your item definitions.
-   When hashing file contents on the node, `sha256` or `sha256sum` is now used. This program must exist *on the node*.
-   The `bw hash ...` command will print sha256 hashes now.

<br>

## `BW_SCP_ARGS` defaults to the empty string

[This environment variable](env.md#bw_scp_args) used to default to the value of `BW_SSH_ARGS` or, if that was unset, to the empty string. `BW_SSH_ARGS` is used when calling the `ssh` binary on your machine, `BW_SCP_ARGS` for the `scp` binary. Since *some* arguments work for both `ssh` and `scp`, you might have gotten away with setting just `BW_SSH_ARGS` (which implicitly also affected `scp`). This will no longer work.

You must now explicitly set `BW_SCP_ARGS`.

No changes to the repository are required.

<br>

## `bw apply` and `bw verify`: `-s` without matches is an error now

TODO still being discussed in https://github.com/bundlewrap/bundlewrap/pull/874

<br>

## `repo.nodes_matching()` throws `NoSuchTarget` when expressions don't match anything

You will have to catch this exception and decide what to do. Previously, this case was silently ignored.

<br>

## Minor changes

For everything else, please consult the [changelog](https://github.com/bundlewrap/bundlewrap/blob/master/CHANGELOG.md#500).
