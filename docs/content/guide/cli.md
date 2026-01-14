# Command Line Interface

The `bw` utility is BundleWrap's command line interface.

<div class="alert alert-info">This page is not meant as a complete reference. It provides a starting point to explore the various subcommands. If you're looking for details, <code>--help</code> is your friend.</div>

## bw apply

```none
bw apply [-i] mynode
```

The most important and most used part of BundleWrap, `bw apply` will apply your configuration to a set of [nodes](../repo/nodes.py.md). By default, it operates in a non-interactive mode. When you're trying something new or are otherwise unsure of some changes, use the `-i` switch to have BundleWrap interactively ask before each change is made.

## bw verify

Inspect the health or 'correctness' of a node without changing it.

```none
$ bw verify mynode
i ╭────────────────────────────────┬───────┬──────┬─────┬─────────┬────────┬──────────╮
i │ node                           │ items │ good │ bad │ unknown │ health │ duration │
i ├────────────────────────────────┼───────┼──────┼─────┼─────────┼────────┼──────────┤
i │ mynode                         │   979 │  979 │   0 │       0 │ 100.0% │      15s │
i ╰────────────────────────────────┴───────┴──────┴─────┴─────────┴────────┴──────────╯
```

## bw lock

Manages [locks](locks.md) on nodes.

## bw run

Directly execute commands on nodes.

```none
$ bw run mygroup "uname -a"
```

As with most commands that accept node names, you can also give a `group` name or any combination of node and group names, separated by commas (without spaces, e.g. `node1,group2,node3`). A third option is to use a bundle selector like `bundle:my_bundle`. It will select all nodes with the named `bundle`. You can freely mix and match node names, group names, and bundle selectors.

Negation is also possible for bundles and groups. `!bundle:foo` will add all nodes without the foo bundle, while `!group:foo` will add all nodes that aren't in the foo group.

## bw ipmi

Directly execute `ipmitool` commands on nodes which have IPMI configured.

<div class="alert alert-info">Needs <a href="https://github.com/ipmitool/ipmitool">ipmitool</a> installed on the machine running <code>bw</code>.</div>

```none
$ bw ipmi mynode "chassis status"
› mynode System Power         : on
› mynode Power Overload       : false
› mynode Power Interlock      : inactive
› mynode Main Power Fault     : false
› mynode Power Control Fault  : false
› mynode Power Restore Policy : always-on
› mynode Last Power Event     :
› mynode Chassis Intrusion    : inactive
› mynode Front-Panel Lockout  : inactive
› mynode Drive Fault          : false
› mynode Cooling/Fan Fault    : false

i ╭────────┬─────────────┬──────╮
i │ node   │ return code │ time │
i ├────────┼─────────────┼──────┤
i │ mynode │           0 │ 0s   │
i ╰────────┴─────────────┴──────╯
```

## bw debug

```none
$ bw debug
bundlewrap X.Y.Z interactive repository inspector
> You can access the current repository as 'repo'.
>>> len(repo.nodes)
121
```

This command will drop you into a Python shell with direct access to BundleWrap's [API](api.md). Once you're familiar with it, it can be a very powerful tool.

## bw plot

<div class="alert alert-info">You'll need <a href="http://www.graphviz.org">Graphviz</a> installed on your machine for this to be useful.</div>

```none
$ bw plot node mynode | dot -Tsvg -omynode.svg</code></pre>
```

You won't be using this every day, but it's pretty cool. The above command will create an SVG file (you can open these in your browser) that shows the item dependency graph for the given node. You will see bundles as dashed rectangles, static dependencies (defined in BundleWrap itself) in green, auto-generated dependencies (calculated dynamically each time you run `bw apply`) in blue and dependencies you defined yourself in red.

It offers an interesting view into the internal complexities BundleWrap has to deal with when figuring out the order in which your items can be applied to your node.

## bw stats

## bw test

```none
$ bw test
✓ node1  samba  pkg_apt:samba
✘ node1  samba  file:/etc/samba/smb.conf

[...]

+----- traceback from worker ------
|
|  Traceback (most recent call last):
|    File "bundlewrap/concurrency.py", line 78, in _worker_process
|      return_value = target(*msg['args'], **msg['kwargs'])
|    File "&lt;string&gt;", line 378, in test
|  BundleError: file:/etc/samba/smb.conf from bundle 'samba' refers to missing file '/path/to/bundlewrap/repo/bundles/samba/files/smb.conf'
|
+----------------------------------
```

This command is meant to be run automatically like a test suite after every commit. It will try to catch any errors in your bundles and file templates by initializing every item for every node (but without touching the network).

## bw nodes/items/groups/metadata

Provides introspection into the assets in your repository.

Some Examples:

```none
$  bw nodes lambda:'node.in_group("location") and not node.in_group("linux")'
loc.dev.printer
loc.dev.toaster
loc.dev.pizza-oven
```

```none
$ bw items --blame mynode
╭───────────────────────────┬───────────────────────────────────╮
│ bundle name               │ items                             │
├───────────────────────────┼───────────────────────────────────┤
│ apt                       │ action:apt_update                 │
│                           │ action:apt_upgrade                │
│                           │ directory:/etc/apt/sources.list.d │
│                           │ file:/etc/apt/sources.list        │
│                           │ …                                 │
╰───────────────────────────┴───────────────────────────────────╯
```

```none
$ bw groups | grep aws
aws-customer1
aws-customer2
aws-customer3
```

```none
$ bw metadata -k 'apt/packages' -- mynode
{
    "apt": {
        "packages": {
            "apt-transport-https": {
                "before": [
                    "pkg_apt:"
                ]
            },
            "at": {},
            "bash-completion": {},
            "bind9-dnsutils": {},
            "biosdevname": {
                "installed": false
            },
            …
        }
    }
}

$ bw metadata -k 'apt/packages/bind9-dnsutils' --blame -- mynode
╭─────────────────────────────┬──────────────────────────╮
│ path                        │ source                   │
├─────────────────────────────┼──────────────────────────┤
│ apt/packages/bind9-dnsutils │ metadata_defaults:ubuntu │
╰─────────────────────────────┴──────────────────────────╯
```

## bw pw

Encodes, Decodes or generates [secrets and passwords](secrets.md) with the repos secret-keys, to be securely stored in metadata. The usual process here is to auto-generate all passwords that are only used by other managed components (ie. database passwords which will be generated for both, the database and the application) so that they can be rotated regularly without too much manual labour. The `bw pw` tools can then be used to introspect these keys in the case they are needed for manual interaction.

Derive human-readable password from string (same as `repo.vault.human_password_for()`)

```none
$ bw pw -H 'root user node1'
Faidr-Hic-Pund-Gek-89
```

Derive password from string (same as `repo.vault.encrypt()`)

```none
bw pw -p 'some secret'
nwOjZXIg48OwAyqqGpwMWMdCgHGZsIRf
```

Encrypt secret for use in metadata (same as `repo.vault.encrypt()`):

```none
$ bw pw -e 'some secret'
encrypt$gAAAAABpZ4vzVdXaQfwPe3-T3Pl0bkBU0cDM1uKGYVYswZ6DKwOHCxcAnDas2arGZS0kv40mtdb9a6sNEb0Fh60TB_Igu5uEAg==
```

## bw repo

Tools to generate a new repo or a new bundle in a repo

```none
$ bw repo create
$ bw bundle create mybundle
```

## bw diff

Show differences between two or more nodes. Generates a list of items that are different together with their item-hash. Use `bw items` to further inspect them.

```none
$ bw diff mynode yournode
--- mynode
+++ yournode
-user:root	09b3124df67ecaebae1d740f9985c3bcfa62492cf114b23026028cf1eb457c75
+user:root	90c5e492990c968838b6ea94976b1f463ccebd8cc2464921032bd5ccad752ac8
```

## bw hash

Generate the SHA256 hash for nodes, groups, lambdas or items. The hash can be used to indicate if a single item within the selection has changed. This can be used for automatic deploys or change-notifications.

```none
$ bw hash mynode
d063cfc437616f7753accf990e43ceece4b2fb92e51ea0314de0effc6ae1fa81

$ bw hash ubuntu-24.04
51e5099152418033e002bace2a34d612815df759b18b15106cb462af1b42bf17

$ bw hash mynode user:root
09b3124df67ecaebae1d740f9985c3bcfa62492cf114b23026028cf1eb457c75
```

## bw generate-completions

Generates or updates a file named `.bw_shell_completion_targets` in the repo-dir to be used with [argcomplete](https://kislyuk.github.io/argcomplete/).
