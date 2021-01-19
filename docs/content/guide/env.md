# Environment Variables

## `BW_ADD_HOST_KEYS`

As BundleWrap uses OpenSSH to connect to hosts, host key checking is involved. By default, strict host key checking is activated. This might not be suitable for your setup. You can set this variable to `1` to cause BundleWrap to set the OpenSSH option `StrictHostKeyChecking=no`.

You can also use `bw -a ...` to achieve the same effect.

<br>

## `BW_COLORS`

Colors are enabled by default. Setting this variable to `0` tells BundleWrap to never use any ANSI color escape sequences.

<br>

## `BW_DEBUG_LOG_DIR`

Set this to an existing directory path to have BundleWrap write debug logs there (even when you're running `bw` without `--debug`).

<div class="alert alert-info">Debug logs are verbose and BundleWrap does not rotate them for you. Putting them on a tmpfs or ramdisk will save your SSD and get rid of old logs every time you reboot your machine.</div>

<br>

## `BW_GIT_DEPLOY_CACHE`

Optional cache directory for <a href="../../items/git_deploy/#bw_git_deploy_cache">`git_deploy`</a> items.

<br>

## `BW_HARDLOCK_EXPIRY`

[Hard locks](locks.md) are automatically ignored after some time. By default, it's `"8h"`. You can use this variable to override that default.

<br>

## `BW_IDENTITY`

When BundleWrap [locks](locks.md) a node, it stores a short description about "you". By default, this is the string `$USER@$HOSTNAME`, e.g. `john@mymachine`. You can use `BW_IDENTITY` to specify a custom string. (No variables will be evaluated in user supplied strings.)

<br>

## `BW_ITEM_WORKERS` and `BW_NODE_WORKERS`

BundleWrap attempts to parallelize work. These two options specify the number of nodes and items, respectively, which will be handled concurrently. To be more precise, when setting `BW_NODE_WORKERS=8` and `BW_ITEM_WORKERS=2`, BundleWrap will work on eight nodes in parallel, each handling two items in parallel.

You can also use the command line options `-p` and `-P`, e.g. `bw apply -p ... -P ... ...`, to achieve the same effect. Command line arguments override environment variables.

There is no single default for these values. For example, when running `bw apply`, four nodes are being handled by default. However, when running `bw test`, only one node will be tested by default. `BW_NODE_WORKERS` and `BW_ITEM_WORKERS` apply to *all* these operations.

Note that you should not set these variables to very high values. First, it can cause high memory consumption on your machine. Second, not all SSH servers can handle massive parallelism. Please refer to your OpenSSH documentation on how to tune your servers for these situations.

<br>

## `BW_MAX_METADATA_ITERATIONS`

Sets the limit of how often metadata reactors will be run for a node before BundleWrap calls it a loop and terminates with an exception. Defaults to `1000`.

<br>

## `BW_REPO_PATH`

Set this to a path pointing to your BundleWrap repository. If unset, the current working directory is used. Can be overridden with `bw --repository PATH`. Keep in mind that `bw` will also look for a repository in all parent directories until it finds one.

<br>

## `BW_SOFTLOCK_EXPIRY`

[Soft locks](locks.md) are automatically removed from nodes after some time. By default, it's `"8h"`. You can use this variable to override that default.

<br>

## `BW_SSH_ARGS`

Extra arguments to include in every call to `ssh` BundleWrap makes. Set this to "-F ~/.ssh/otherconf" to use a different SSH config with BundleWrap. Defaults to `""`.

<br>

## `BW_SCP_ARGS`

Extra arguments to include in every call to `scp` BundleWrap makes. Defaults to the value of `BW_SSH_ARGS`.

<br>

## `BW_TABLE_STYLE`

By default, BundleWrap uses Unicode box-drawing characters at various points in its output. Setting this env var to one of the following values changes that behavior:

<table>
<tr><td><code>ascii</code></td><td>use only simple ASCII characters to render tables (useful if your font doesn't properly align box-drawing characters)</td></tr>
<tr><td><code>grep</code></td><td>make output more <code>grep</code>- and <code>cut</code>-friendly</td></tr>
</table>

<br>

## `BW_VAULT_DUMMY_MODE`

Setting this to `1` will make `repo.vault` return dummy values for every [secret](secrets.md). This is useful for running `bw test` on a CI server that you don't want to trust with your `.secrets.cfg`.
