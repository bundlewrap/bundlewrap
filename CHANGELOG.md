# 4.23.0

2025-06-03

* added support for shell autocompletion using `argcomplete`
* added `bw items --blame`
* defaults for `BW_NODE_WORKERS` are now consistent across all of bundlewrap
  * This especially means that `bw run` and `bw ipmi` will now also use 4 (four) workers by default if you did not set`BW_NODE_WORKERS` manually
* `IOManager` can now be used as a context manager
  * That means you can now do `with io: ...` instead of having to use `try: ... finally:`
* added job information for running `unless` actions
* added `bw lock show --hide-not-locked`
* fixed `bw repo create` so TOML nodes work out of the box
* removed dependency on deprecated `pkg_resources` for python >= 3.10

# 4.22.0

2025-03-20

* fixed a bug where the original signal handlers were not restored on exit
* fixed a bug where `io` could get (de)activated multiple times
* add tab completion to `bw debug`
* added better debug messages for missing faults in files
* added warning on `bw lock add` if node already contains other locks
* add history saving and loading to `bw debug`
* improve handling of ssh connections in `git_deploy` items
* add `bw ipmi`
* DOCS: fix documentation for `metadata.py`


# 4.21.0

2024-11-14

* fixed dependency loops created by bw itself ("concurrency blockers" are implemented differently now)
* fixed a regression in `pkg_pip`: packages were incorrectly identified as "not installed"
* added: `pkg_apt` packages will now be marked as manually installed, thus preventing auto-cleanup mechanisms from deleting them
* added support for DNF 5
* added: `postgres_roles` now support password hashes other than md5
* added `bw apply --no-skipped-items` to not show skipped items
* improved `directory` items: try to avoid accidental data loss by using `rm -f` instead of `rm -rf`

# 4.20.0

2024-08-07

* added `bw metadata --resolve-faults`
* added runlevel support for `svc_openrc`
* added purge support for `routeros`
* experimental: added support for `--break-system-packages` to `pkg_pip`


# 4.19.0

2024-06-25

* added hook `node_ssh_connect`
* improved flickering in most terminals


# 4.18.0

2024-04-01

* added support for Python 3.12
* removed support for Python 3.7
* added `download_timeout` for file items
* performance improvements
* improved display of long-running jobs
* improved handling of connection errors
* improved handling of services on OpenBSD
* fixed fixing of symlink ownership
* fixed detection of installed packages with `pacman`
* fixed handling of binary files with `bw pw -f`
* fixed missing setuptools dependency
* fixed `block_concurrent()` not working if item provides canned actions


# 4.17.2

2023-05-05

* fixed `bw hash` trying to hash actions


# 4.17.1

2023-05-05

* fixed `username` node attribute not being respected during some operations
* fixed detection of `enabled-runtime` state for systemd services
* fixed handling of connection errors to routeros nodes
* fixed boolean type conversion for routeros items
* fixed unhelpful tracebacks after AttributeError in reactors and such


# 4.17.0

2023-02-18

* added `key_command` for `.secrets.cfg`
* added `node.rename()` for TOML nodes
* improved logging for `routeros` items


# 4.16.1

2023-01-19

* fixed connections to RouterOS being reused after errors
* fixed non-strings in sets crashing `bw metadata`


# 4.16.0

2022-11-27

* added support for Python 3.11
* improved performance of dynamic node attributes in lambda selectors
* fixed type handling in `dconf` items
* fixed `os_version` not being useable in TOML files
* fixed `pkg_apt` being unable to remove 'essential' packages
* fixed `bw items -w` crashing with `download` content type


# 4.15.0

2022-09-19

* added exception handling for `bw nodes -a`
* added color for `None` in `bw nodes -a` output
* reworked `ErrorContext` exception chain
* improved error messages for malformed bundles
* fixed `FaultUnavailable` exception when using unless with Faults


# 4.14.2

2022-06-24

* fixed `bw nodes -a all` and `bw groups -a all`
* fixed handling of duplicate toml nodes
* fixed some internal type conversions


# 4.14.1

2022-06-24

* fixed sorting of lists and tuples in `bw nodes`


# 4.14.0

2022-06-24

* added `BW_TABLE_STYLE=csv`
* added `dconf` items
* added dynamic node attributes
* added `node_count` read-only group attribute
* improved performance loading toml files
* improved dependency loop debugging
* fixed `repo.vault.decode_file_as_base64()` in dummy mode
* fixed a crash in `bw plot node`
* fixed reporting of unknown groups


# 4.13.6

2022-01-28

* show file path on TOML parse error
* improved performance of `bw test -M`
* fixed `bw plot groups-for-node` not showing all memberships


# 4.13.5

2022-01-15

* fixed some issues in `bw plot`
* fixed `zfs_dataset` not allowing unmanaged pools
* fixed `zfs_dataset` creating deps based on identical mountpoints
* fixed `node.metadata` not being recognized as a Mapping


# 4.13.4

2021-12-01

* fixed addressing for some routeros items
* fixed occasional socket errors for routeros items


# 4.13.3

2021-11-18

* fixed empty comments not returned by RouterOS API


# 4.13.2

2021-11-24

* fixed concurrency issues with RouterOS
* added workaround for setting `comment` on RouterOS items


# 4.13.1

2021-11-10

* fixed tomlkit types leaking into nodes/metadata


# 4.13.0

2021-11-05

* added support for Python 3.10
* added filtering for internal attributes in `bw items`
* added `pkg_pamac`
* added `svc_freebsd`
* added support for arbitrary `zfs_dataset` attributes
* relaxed metadata type conversion
* fixed `pkg_pip` not showing error output
* fixed concurrent execution of some package manager operations


# 4.12.0

2021-09-22

* added `test_with` to `file` items
* added `download` `content_type` to `file` items
* added `bw pw`


# 4.11.2

2021-08-16

* fixed detection of non-existing `zfs_pools`
* fixed `config` and `ashift` attributes of `zfs_pool` items not being marked as `when_creating`
* fixed `when_creating` attributes not being shown in diffs on apply


# 4.11.1

2021-08-11

* fixed another premature `MetadataPersistentKeyError`


# 4.11.0

2021-08-11

* added `zfs_pool` and `zfs_dataset` items
* added `bw plot reactors`
* added `bw lock show -i`
* improved metadata reactor performance and debug logging
* improved exception handling during `bw apply`
* CTRL+C now results in exit code 130
* fixed directory permissions not being applied reliably with GNU `chmod`
* fixed `bw test -p` not catching some invalid returns
* fixed item name validation allowing empty names
* fixed display of "missing" attributes
* fixed display of created directories


# 4.10.1

2021-07-07

* fixed a premature `MetadataPersistentKeyError`


# 4.10.0

2021-07-06

* enable iteration over Faults
* fixed using sets as metadata in TOML nodes


# 4.9.0

2021-06-28

* added `repo.vault.cmd()`
* postgres items can now be used with `doas` instead of `sudo`
* improved error reporting of `git_deploy`
* fixed dependencies being skipped when using `bw apply -o`
* fixed user and group management on BSD


# 4.8.2

2021-05-27

* fixed clobbered env vars for `git_deploy`
* fixed `pkg_pip` failing with underscores in package names


# 4.8.1

2021-05-19

* improved exception reporting for `bw verify` and `git_deploy`
* fixed metadata source attribution in `bw metadata -b`
* fixed `AttributeError` in `bw diff -i -b`
* fixed late detection of duplicate items
* fixed `bw diff` not showing anything useful for single nodes
* fixed and optimized checking order of item skip conditions
* fixed garbled output in files produced by `BW_DEBUG_LOG_DIR`


# 4.8.0

2021-05-02

* added support for RouterOS
* fixed k8s objects not being retrieved with the correct apiVersion


# 4.7.1

2021-03-29

* fixed `bw lock show` hiding output if it failed to connect to any host
* fixed `bw test -m` not handling cdict mismatches properly


# 4.7.0

2021-03-24

* added `skip` item attribute
* added `before` and `after` soft dependencies
* added `--only` and `--skip` to `bw verify`
* improved `bw plot node` to properly show all 7 types of item dependencies
* fixed metadata reactors being able to corrupt metadata in some cases


# 4.6.0

2021-02-25

* added `pkg_apk` and `svc_openrc` items
* actions can now be inspected with `bw items`
* `bw test -d` now shows a diff for config changes
* fixed display of strings in `bw items --attrs`


# 4.5.1

2021-02-19

* fixed actions that set `None` as `expected_return_code`


# 4.5.0

2021-02-19

* added diffs to the default output of `bw apply` and `bw verify`
* added `bw apply --no-diff`
* added `bw verify --no-diff`
* added `pkg_freebsd`
* added canned `stop` actions for services
* added `masked` attribute for `svc_systemd`
* added multiple expected return codes for actions
* improved error message for incompatible types in diff
* fixed group management on FreeBSD
* fixed types from tomlkit not being diffable
* fixed using Faults for user password salts
* fixed `bw repo create` clobbering existing repos


# 4.4.2

2021-01-22

* full tracebacks are now shown by default for exceptions in file templates
* fixed a `RuntimeError` related to a metadata concurrency issue


# 4.4.1

2021-01-20

* fixed `bw test -p` quietness
* fixed dependency loop detection between empty tags
* fixed missing dict methods on `node.metadata`


# 4.4.0

2021-01-20

* added `Fault.as_htpasswd_entry()`
* added tag inheritance through `bundle.py`
* optimized performance of metadata generation based on `@metadata_reactor.provides()`
* fixed `TypeError` in `bw plot`
* fixed `needs` from tags not being applied to items
* fixed unused tags not passing on their dependencies
* removed experimental metadata caching


# 4.3.0

2020-12-23

* added support for Python 3.9
* added supergroups as a reverse direction for the existing subgroups
* added `bundle.py`
* added metadata caching (EXPERIMENTAL)
* added `@metadata_reactor.provides()` (EXPERIMENTAL)
* reworked item selectors
* sorted summary table for `bw apply`
* fixed handling of k8s apiVersions
* fixed canned actions not being skipped if their parent item is skipped
* pipe output to `less` if there are too many lines


# 4.2.2

2020-10-30

* fixed tomlkit types not being accepted as statedict values


# 4.2.1

2020-10-15

* fixed unintended Fault evaluation in metadata collision error message
* fixed sorting of Faults with other types
* fixed display of paged output on large macOS terminals
* fixed svc_openbsd being applied concurrently
* fixed services being reloaded and restarted at the same time
* fixed possible mangling of group metadata from items.py


# 4.2.0

2020-09-21

* added `BW_GIT_DEPLOY_CACHE`
* added `lock_dir` node attribute
* added `pip_command` node attribute
* Fault callbacks can now accept some unhashable parameters (such as dicts)


# 4.1.1

2020-08-12

* improved reporting of invalid types in metadata
* improved error output of `bw test -m`
* fixed recognition of JSON files as text
* fixed a rare case of nodes not having their metadata built to completion
* fixed a column sorting issue in `bw nodes`


# 4.1.0

2020-07-27

* added `bw test --quiet`
* `apply_start` hook can now raise GracefulApplyException
* performance improvements in metadata generation
* improved reporting of persistent metadata KeyErrors
* clashing metadata keys are now allowed for equal values
* git_deploy: fixed attempted shallow clones over HTTP
* k8s: improved handling of absent `apiVersion`
* fixed `cascade_skip` not affecting recursively skipped items
* fixed `bw metadata -b -k`
* fixed metadata reactors seeing their own previous results
* fixed SCM information being returned as bytes


# 4.0.0

2020-06-22

* new metadata processor API (BACKWARDS INCOMPATIBLE)
* removed `template_node` node attribute (BACKWARDS INCOMPATIBLE)
* removed support for Python 2.7 (BACKWARDS INCOMPATIBLE)
* removed support for Python 3.4 (BACKWARDS INCOMPATIBLE)
* removed support for Python 3.5 (BACKWARDS INCOMPATIBLE)
* removed `members_add/remove` attribute for groups (BACKWARDS INCOMPATIBLE)
* removed `bw --adhoc-nodes` (BACKWARDS INCOMPATIBLE)
* added `locking_node` node attribute
* added `bw diff`
* added `bw metadata -b`
* added `bw metadata --hide-defaults`
* added `bw metadata --hide-reactors`
* added `bw metadata --hide-groups`
* added `bw metadata --hide-node`
* added `git_deploy` items (formerly a plugin)
* added paging and color-coding for metadata sources to `bw metadata`
* removed `bw metadata --table`, now done automatically (BACKWARDS INCOMPATIBLE)
* removed `bw repo plugin` (BACKWARDS INCOMPATIBLE)
* removed `bw test --secret-rotation` (BACKWARDS INCOMPATIBLE)
* renamed `bw test --metadata-collisions` to `bw test --metadata-conflicts` (BACKWARDS INCOMPATIBLE)
* reworked passing multi-value options on CLI (BACKWARDS INCOMPATIBLE)
* `bw apply` will now exit with return code 1 if even a single item fails
* `items/` is now searched recursively
* failed items will now show what commands they ran and what their output was


# 3.9.0

2020-05-04

* added lambda expressions for CLI node selection
* added `groups` attribute to nodes
* added support for Python 3.8
* k8s: bumped `apiVersion` where appropriate
* fixed handling of `apiVersion` and `status`
* fixed KeyError on k8s item collision


# 3.8.0

2020-01-09

* `k8s_raw`: added support for items without a namespace
* `k8s_raw`: fixed overriding resource name in YAML
* `k8s_raw`: allow using builtin item types if there are no actual conflicts
* decryption keys can now be set within encrypted files
* improved detection of incorrect metadata processor usage
* fixed excessive skipping of items because of concurrency dependencies
* fixed `preceded_by` not working for actions


# 3.7.0

2019-10-07

* Faults are now accepted as item attribute values
* Filter objects, iterators and such can now be used as item attribute values
* `BW_VAULT_DUMMY_MODE` will now yield dummy passwords of requested length
* added `repo.vault.random_bytes_as_base64_for()`


# 3.6.2

2019-07-25

* fixed `None` not being accepted as a file/directory mode
* fixed overriding resource name in k8s manifests


# 3.6.1

2019-03-12

* Faults can now be sorted
* fixed detection of runtime-enabled `svc_systemd`
* fixed resolving nested Faults


# 3.6.0

2019-02-27

* added `bw apply --only`
* added `Fault.b64encode()`
* added support for using Faults in k8s manifests
* improved display of some skipped items
* improved error handling during `bw apply`
* improved handling of offline nodes in `bw verify`
* fixed corrupted hard lock warning
* fix interactively overwriting symlinks/dirs


# 3.5.3

2018-12-27

* added error message when trying to access node bundles from `members_add/remove`
* improved performance for file verification
* fixed symlinks being mistaken for directories in some circumstances


# 3.5.2

2018-12-11

* fixed IO activation/deactivation when using bw as a library
* fixed `atomic()` being removed prematurely during metadata processing


# 3.5.1

2018-07-08

* added support for Python 3.7
* fixed merged metadata not overwriting atomic() values


# 3.5.0

2018-06-12

* added `template_node` node attribute
* actions are now included in `bw verify`
* improved error message for KeyErrors in Mako templates
* fixed hashing for filenames with escaped characters
* fixed AttributeError when reverse-depending on `bundle:` items


# 3.4.0

2018-05-02

* added k8s_clusterrole items
* added k8s_clusterrolebinding items
* added k8s_crd items
* added k8s_networkpolicy items
* added k8s_raw items
* added k8s_role items
* added k8s_rolebinding items
* added Kubernetes item preview with `bw items -f`
* improved handling of exceptions during `bw verify` and `bw apply`
* improved progress display during `bw run`


# 3.3.0

2018-03-09

* added experimental support for Kubernetes
* some hooks can now raise an exception to skip nodes
* fixed ED25519 public keys not being recognized as text files
* fixed package names with hyphens for pkg_openbsd
* fixed diff for user groups


# 3.2.1

2018-01-08

* fixed metadata key filter for `bw metadata --blame`
* fixed pkg_openbsd reported incorrectly as having having wrong flavor installed
* fixed crash when declining actions interactively


# 3.2.0

2018-01-01

* items skipped because of "unless" or "not triggered" are no longer shown during `bw apply`
* added `BW_SCP_ARGS`
* added `bw metadata --blame`
* added `bw test --metadata-keys`
* added flavor support to pkg_openbsd
* fixed changing symlink targets if previous target is a dir
* fixed display of some item attributes during `bw apply` and `bw verify`
* fixed handling of postgres DBs/roles with hyphens in them


# 3.1.1

2017-10-24

* will now detect bad wrappers around metadata processors
* fixed crash in `bw plot`
* fixed cut off status lines


# 3.1.0

2017-10-10

* added pkg_opkg items
* added `bw test -s`
* improved error messages for unknown reverse triggers
* fixed hash_method md5 on user items
* fixed cursor sometimes not being restored


# 3.0.3

2017-10-04

* dropped support for Python 3.3
* fixed `bw` trying to hide the cursor without a TTY present
* fixed `ImportError` with Python 2.7


# 3.0.2

2017-10-04

* improved status line
* `bw test` is now more responsive to SIGINT
* sorted bundle and group lists in `bw nodes` output
* fixed an issue with symlinks failing if fixing both target and ownership
* fixed `bw run` with dummy nodes
* fixed progress exceeding 100% during `bw apply`
* fixed progress intermittently being stuck at 100% during `bw test`
* fixed incorrent display of fixed item properties
* fixed `bw metadata --table` being unable to show None
* fixed `bw metadata` hiding KeyErrors


# 3.0.1

2017-09-25

* fixed `bw run`
* fixed `bw test -e`


# 3.0.0

2017-09-24

* new metadata processor API and options (BACKWARDS INCOMPATIBLE)
* files, directories, and symlinks now have defaults for owner, group, and mode (BACKWARDS INCOMPATIBLE)
* overhauled options and output of `bw groups` (BACKWARDS INCOMPATIBLE)
* overhauled options and output of `bw nodes` (BACKWARDS INCOMPATIBLE)
* overhauled options and output of `bw run` (BACKWARDS INCOMPATIBLE)
* overhauled options of `bw test` (BACKWARDS INCOMPATIBLE)
* svc_systemd services are now 'enabled' by default (BACKWARDS INCOMPATIBLE)
* `bw items --file-preview` no longer uses a separate file path argument (BACKWARDS INCOMPATIBLE)
* removed `bw apply --profiling` (BACKWARDS INCOMPATIBLE)
* removed `Item.display_keys()` (BACKWARDS INCOMPATIBLE)
* changed return value of `Item.display_dicts()` (BACKWARDS INCOMPATIBLE)
* changed `Item.BLOCK_CONCURRENT` into a class method (BACKWARDS INCOMPATIBLE)
* removed `repo.vault.format()` (BACKWARDS INCOMPATIBLE)
* removed env vars: BWADDHOSTKEYS, BWCOLORS, BWITEMWORKERS, BWNODEWORKERS (BACKWARDS INCOMPATIBLE)


# 2.20.1

2017-09-21

* improved performance of metadata processors
* pkg_* and svc_* items no longer throw exceptions when their commands fail
* fixed BW_DEBUG_LOG_DIR with `bw debug`
* fixed 'precedes' attribute for actions


# 2.20.0

2017-08-15

* added progress info shown on SIGQUIT (CTRL+\\)
* added pkg_snap items
* fixed checking for dummy nodes during `bw lock`
* fixed handling of missing Faults for actions
* fixed handling of missing Faults for `bw items -w`


# 2.19.0

2017-07-05

* actions can now receive data over stdin
* added `Node.magic_number`
* added `bw apply --resume-file`
* added hooks for `bw lock`
* added `bw metadata --table`


# 2.18.1

2017-06-01

* fixed display of comments for actions


# 2.18.0

2017-05-22

* added encoding and collation to postgres_db items
* added the 'comment' attribute for all items
* fixed group deletion
* fixed accidental modification of lists in statedicts


# 2.17.1

2017-04-19

* fixed parent groups not being removed by subgroups' members_remove
* fixed `bw lock` trying to connect to dummy nodes


# 2.17.0

2017-03-26

* pkg_apt: added start_service attribute
* pkg_apt: added support for multiarch packages
* improved reporting of exceptions in metadata processors
* fixed package cache leaking across nodes


# 2.16.0

2017-02-23

* added `BW_TABLE_STYLE`
* added more Unicode tables
* added number of bundles and metadata processors to `bw stats`
* added oraclelinux to `OS_FAMILY_REDHAT`
* added option to ignore running status of systemd services
* improved circular dependency debugging
* improved reporting of dependency errors
* fixed avoidance of circular dependencies
* fixed dealing with SUID and SGID on directories
* fixed debug logging on Python 2.7
* fixed duplicates in `Group.subgroups`
* fixed handling of subgroup patterns in `bw plot group`


# 2.15.0

2017-01-19

* added item and attribute arguments to `bw items`
* added orphaned bundle warnings to `bw test`
* fixed regression when removing soft locks


# 2.14.0

2017-01-16

* added key filtering to `bw metadata`
* added `repo.vault.human_password_for()`
* added `BW_REPO_PATH` and `bw --repo-path`
* quotes are no longer required around commands with `bw run`
* fixed intermittent circular dependencies with multiple custom items using BLOCK_CONCURRENT
* fixed exception when removing non-existent soft lock


# 2.13.0

2017-01-05

* added tuple return option to metadata processors
* improved CLI output in various places
* improved performance during dependency processing
* improved performance when checking packages
* fixed hashing of metadata containing sets
* fixed exception with `svc_upstart` when service doesn't exist


# 2.12.2

2016-12-23

* added support for Python 3.6
* changed diff line length limit from 128 to 1024 characters
* fixed deadlock in Group.members_remove
* fixed unknown subgroups not being detected properly


# 2.12.1

2016-12-20

* fixed exception when changing owner of postgres databases
* fixed postgres roles requiring a password even when deleted
* fixed incorrect exit codes in some situations with `bw test`


# 2.12.0

2016-11-28

* added `BW_DEBUG_LOG_DIR`
* improved reporting of action failures
* fixed `bw plot groups` and `bw plot groups-for-node`
* fixed access to partial metadata in `Group.members_add` and `_remove`


# 2.11.0

2016-11-14

* added `bw nodes --inline`
* added `Group.members_add` and `.members_remove`
* fixed symlinks not overwriting other path types
* fixed `precedes` and `triggers` for bundle, tag and type items
* fixed diffs for sets and tuples


# 2.10.0

2016-11-03

* added pkg_dnf items
* added rudimentary string operations on Faults
* added Fault documentation
* added `bw test --config-determinism` and `--metadata-determinism`
* improved debugging facilities for metadata processor loops
* improved handling and reporting of missing Faults


# 2.9.1

2016-10-18

* fixed `bw verify` without `-S`
* fixed asking for changes to directory items


# 2.9.0

2016-10-17

* added directory purging
* added `bw --adhoc-nodes`
* improve handling of unknown nodes/groups
* improvements to `bw nodes`


# 2.8.0

2016-09-12

* added `BW_HARDLOCK_EXPIRY` env var
* added `bw hash --group`
* added `subgroup_patterns`
* added `bw test --ignore-missing-faults`
* added `node.cmd_wrapper_inner` and `_outer`
* added `node.os_version`
* fixed exception handling under Python 2
* fixed partial metadata not being completed in some cases


# 2.7.1

2016-07-15

* improved responsiveness to SIGINT during metadata generation
* fixed SIGINT handling on Python 2.7


# 2.7.0

2016-07-15

* `bw lock show` can now show entire groups
* `bw` can now be invoked from any subdirectory of a repository
* added `bw hash --metadata`
* added `bw nodes --attrs`
* added `repo.vault.format`
* added graceful handling of SIGINT
* added log level indicator to debug output
* added `node.dummy` attribute
* added `BW_SSH_ARGS` environment variable
* `bash` is no longer required on nodes
* `node.os` and `node.use_shadow_passwords` can now be set at the group level
* sets are now allowed in metadata
* optimized execution of metadata processors
* fixed `bw apply --force` with unlocked nodes
* fixed `bw test` not detecting merge of lists in unrelated groups' metadata
* fixed installation of some pkg_openbsd
* fixed piping into `bw apply -i`
* fixed handling user names with non-ASCII characters
* fixed skipped and failed items sometimes being handled incorrectly
* fixed error with autoskipped triggered items
* fixed skip reason for some soft locked items


# 2.6.1

2016-05-29

* fixed accidentally changed default salt for user items


# 2.6.0

2016-05-29

* added support for OpenBSD packages and services
* added soft locking mechanism
* added `enabled` option for `svc_systemd`
* fixed running compound commands


# 2.5.2

2016-05-04

* fixed compatibility with some exotic node shells
* fixed quitting at question prompts
* fixed creating files with content_type 'any'


# 2.5.1

2016-04-07

* fixed false positive on metadata collision check


# 2.5.0

2016-04-04

* improved performance and memory usage
* added metadata conflict detection to `bw test`
* added metadata type validation
* added `BW_VAULT_DUMMY_MODE`
* added q(uit) option to questions
* output disabled by default when using as a library
* fixed `bw hash -d`
* fixed excessive numbers of open files
* fixed partial metadata access from metadata processors


# 2.4.0

2016-03-20

* added `bw plot group`
* added `bw plot groups-for-node`
* `bw` will now check requirements.txt in your repo before doing anything
* improved output of `--help`
* metadata processors now have access to partial node metadata while it is being compiled
* fixed `bw test` when using more than the default number of node workers
* fixed passing Faults to `postgres_role` and `users`
* fixed detection of non-existent paths on CentOS and others


# 2.3.1

2016-03-15

* fixed handling of 'generate' keys for `repo.vault`


# 2.3.0

2016-03-15

* added `repo.vault` for handling secrets
* circular dependencies are now detected by `bw test`
* fixed handling of broken pipes in internal subprocesses
* fixed previous input being read when asking a question
* fixed reading non-ASCII templates on systems with ASCII locale
* `bw apply` and `bw verify` now exit with return code 1 if there are errors


# 2.2.0

2016-03-02

* added item tagging
* added `bw apply --skip`
* fixed newline warning on long diff files
* fixed calling `bw` without arguments


# 2.1.0

2016-02-25

* added `bw stats`
* added `bw items --file-preview`
* added hooks for `bw test`
* reason for skipping an item is now displayed in regular output
* fixed exception handling for invalid cdicts/sdicts
* fixed handling of SSH errors
* fixed broken diffs caused by partial file downloads
* fixed interactive prompts sometimes not reading input correctly


# 2.0.1

2016-02-22

* fixed display of failed actions
* updated display of interactive lock override prompt
* improved robustness of internal output subsystem


# 2.0.0

2016-02-22

* added support for Python 3.3+
* switched from Fabric/Paramiko to OpenSSH
* removed SSH and sudo passwords **(BACKWARDS INCOMPATIBLE)**
* metadata is now merged recursively **(BACKWARDS INCOMPATIBLE)**
* file items: the source attribute now has a default **(BACKWARDS INCOMPATIBLE)**
* file items: the default content_type is now text **(BACKWARDS INCOMPATIBLE)**
* reworked command line options for `bw verify` **(BACKWARDS INCOMPATIBLE)**
* `cascade_skip` now defaults to `False` if the item is triggered or uses `unless` **(BACKWARDS INCOMPATIBLE)**
* `bw verify` and `bw apply` now show incorrect/fixed/failed attributes
* `bw apply` now uses a status line to show current activity
* generally improved output formatting


# 1.6.0

2016-02-22

* added `bw migrate` **(will be removed in 2.0.0)**
* added warnings for upgrading to 2.0.0 **(will be removed in 2.0.0)**


# 1.5.1

2015-06-11

* clean up local lock files
* fixed detection of some types of directories
* fixed exception spam when trying to load internal attributes as libs


# 1.5.0

2015-05-10

* added postgres_db and postgres_role items
* added `bw verify --only-needs-fixing`
* added `bw verify --summary`
* added `Repository.nodes_in_group()`
* added `verify_with` attribute for file items
* libs now have access to `repo_path`
* user items: fixed asking for password hash change
* file items: fixed `bw items -w` with `content_type: 'any'`
* improved various error messages


# 1.4.0

2015-03-02

* added virtualenv support for pkg_pip
* added reverse syntax for triggers and preceded_by
* lots of fixes and internal improvements around preceded_by


# 1.3.0

2014-12-31

* added pkg_pip items
* added pkg_yum items
* added pkg_zypper items
* added preceded_by item attribute
* fixed detection of non-existing files on CentOS/RHEL
* fixed detection of special files on Arch Linux
* fixed handling UTF-8 output of failed commands


# 1.2.2

2014-10-27

* fixed item classes not being restored after repo serialization


# 1.2.1

2014-10-21

* fixed a critical bug in bundle serialization


# 1.2.0

2014-10-19

* added item generators
* added `bw test --plugin-conflict-error`
* added `bw debug -c`
* improved unicode handling
* fixed logging issues


# 1.1.0

2014-08-11

* added metadata processors
* added `bw metadata`
* added `bw apply --profiling`
* added Repository.nodes_in_all_groups()
* added Repository.nodes_in_any_group()
* added the data subdirectory
* improved various error messages


# 1.0.0

2014-07-19

* API will now remain stable until 2.0.0
* added hooks for actions
* added support for Jinja2 templates
* fixed some CLI commands not terminating correctly


# 0.14.0

2014-07-13

* files, directories and symlinks don't care about ownership and mode by
  default **(BACKWARDS INCOMPATIBLE)**
* Mako file templates can now use include


# 0.13.0

2014-06-19

* added password-based SSH/sudo authentication
* fixed symlink items not checking existing link targets
* fixed exception when triggering skipped items
* output is now prefixed with `node:bundle:item_type:item_name`
* `bw repo debug` is now a top-level command **(BACKWARDS INCOMPATIBLE)**
* `bw repo plot` is now a top-level command **(BACKWARDS INCOMPATIBLE)**
* `bw repo test` is now a top-level command **(BACKWARDS INCOMPATIBLE)**


# 0.12.0

2014-05-11

* added plugins
* added group metadata
* user and group attributes are now optional
* user groups may no longer contain primary group **(BACKWARDS INCOMPATIBLE)**
* improvements to logging and output
* fixed a critical bug preventing per-node customization of bundles
* fixed pkg_apt choking on interactive dpkg prompts
* fixed hashing of plaintext user passwords without salt


# 0.11.2

2014-04-02

* packaging fixes only


# 0.11.1

2014-04-02

* packaging fixes only


# 0.11.0

2014-03-23

* renamed builtin item attribute 'depends' to 'needs' **(BACKWARDS INCOMPATIBLE)**
* removed PARALLEL_APPLY on custom items in favor of BLOCK_CONCURRENT **(BACKWARDS INCOMPATIBLE)**
* added builtin item attribute 'needed_by'
* added canned actions for services
* added deletion of files, groups and users
* simplified output of `bw apply`
* `bw repo test` now also verifies dependencies
* fixed `bw repo test` for files without a template
* fixed triggered actions being run every time
* various fixes and improvements around dependency handling


# 0.10.0

2014-03-08

* removed the 'timing' attribute on actions **(BACKWARDS INCOMPATIBLE)**
* actions are now first-class items
* items can now trigger each other (most useful with actions)
* added System V service item
* added `bw repo test`
* added negated bundle and group selectors to CLI
* can now manage files while ignoring their content
* more control over how actions are run in interactive mode
* bundles can now be assigned to nodes directly
* fixed creating symlinks in nonexistent unmanaged directories


# 0.9.0

2014-02-24

* added 'unless' for actions
* improved exception handling
* fixed actions not triggering in noninteractive mode
* fixed noninteractive installation of Debian packages
* slightly more verbose output


# 0.8.0

2014-02-21

* move from Alpha into Beta stage
* added builtin item attribute 'unless'
* added lightweight git/hg/bzr integration
* added -f switch to `bw apply`
* template context can now be customized
* added Node.has_bundle, .in_group etc.
* fixed a LineBuffer bug
* prevented output of some extraneous whitespace


# 0.7.0

2014-02-16

* added safety checks to prevent diffs of unwieldy files
* added a "text" content type for files
* added support for arbitrary encodings in managed files
* addes systemd and Upstart service items
* added hooks
* added action triggers (for service restarts after config changes)
* lots of new documentation
* better error messages when defining duplicate items
* better dependencies between files, directories and symlinks
* fixed a bug that prevented managing /etc/sudoers


# 0.6.0

2014-01-01

* added actions
* reworked group patterns **(BACKWARDS INCOMPATIBLE)**
* reworked output verbosity **(BACKWARDS INCOMPATIBLE)**
* added support for libs directory
* fixed high CPU load while waiting for interactive response
* various other minor fixes and improvements


# 0.5.0

2013-11-09

* manage users and groups
* manage symlinks
* node locking
* PARALLEL_APPLY setting for items
* manage Arch Linux packages
* plot item dependencies
* encoding fixes for file handling


# 0.4.0

2013-08-25

* manage directories
* manage Debian packages
* UI improvements


# 0.3.0

2013-08-04

* basic file management
* concurrency improvements
* logging/output improvements
* use Fabric for remote operations
* lots of other small improvements


# 0.2.0

2013-07-12

* bundle management
* item APIs
* new concurrency helpers


# 0.1.0

2013-06-16

* initial release
* node and group management
* running commands on nodes
