# Environment Variables

## `BW_ADD_HOST_KEYS`

As BundleWrap uses OpenSSH to connect to hosts, host key checking is involved. By default, strict host key checking is activated. This might not be suitable for your setup. You can set this variable to `1` to cause BundleWrap to set the OpenSSH option `StrictHostKeyChecking=no`.

You can also use `bw -a ...` to achieve the same effect.


## `BW_COLORS`

Colors are enabled by default. Setting this variable to `0` tells BundleWrap to never use any ANSI color escape sequences.


## `BW_IDENTITY`

When BundleWrap [locks](locks.md) a node, it stores a short description about "you". By default, this is the string `$USER@$HOSTNAME`, e.g. `john@mymachine`. You can use `BW_IDENTITY` to specify a custom string. (No variables will be evaluated in user supplied strings.)


## `BW_ITEM_WORKERS` and `BW_NODE_WORKERS`

BundleWrap attempts to parallelize work. These two options specify the number of nodes and items, respectively, which will be handled concurrently. To be more precise, when setting `BW_NODE_WORKERS=8` and `BW_ITEM_WORKERS=2`, BundleWrap will work on eight nodes in parallel, each handling two items in parallel.

You can also use the command line options `-p` and `-P`, e.g. `bw apply -p ... -P ... ...`, to achieve the same effect. Command line arguments override environment variables.

There is no single default for these values. For example, when running `bw apply`, four nodes are being handled by default. However, when running `bw test`, only one node will be tested by default. `BW_NODE_WORKERS` and `BW_ITEM_WORKERS` apply to *all* these operations.

Note that you should not set these variables to very high values. First, it can cause high memory consumption on your machine. Second, not all SSH servers can handle massive parallelism. Please refer to your OpenSSH documentation on how to tune your servers for these situations.


## `BW_SOFTLOCK_EXPIRY`

[Soft locks](locks.md) are automatically removed from nodes after some time. By default, it's eight hours. You can use this variable to override that default.


## `BW_VAULT_DUMMY_MODE`

Setting this to `1` will make `repo.vault` return dummy values for every [secret](secrets.md). This is useful for running `bw test` on a CI server that you don't want to trust with your `.secrets.cfg`.
