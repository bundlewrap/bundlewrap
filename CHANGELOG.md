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
