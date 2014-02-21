0.8.0
=====

2014-02-21

* move from Alpha into Beta stage
* added builtin item attribute 'unless'
* added lightweight git/hg/bzr integration
* added -f switch to `bw apply`
* template context can now be customized
* added Node.has_bundle, .in_group etc.
* fixed a LineBuffer bug
* prevented output of some extraneous whitespace


0.7.0
=====

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


0.6.0
=====

2014-01-01

* added actions
* reworked group patterns (BACKWARDS INCOMPATIBLE)
* reworked output verbosity (BACKWARDS INCOMPATIBLE)
* added support for libs directory
* fixed high CPU load while waiting for interactive response
* various other minor fixes and improvements


0.5.0
=====

2013-11-09

* manage users and groups
* manage symlinks
* node locking
* PARALLEL_APPLY setting for items
* manage Arch Linux packages
* plot item dependencies
* encoding fixes for file handling


0.4.0
=====

2013-08-25

* manage directories
* manage Debian packages
* UI improvements


0.3.0
=====

2013-08-04

* basic file management
* concurrency improvements
* logging/output improvements
* use Fabric for remote operations
* lots of other small improvements


0.2.0
=====

2013-07-12

* bundle management
* item APIs
* new concurrency helpers


0.1.0
=====

2013-06-16

* initial release
* node and group management
* running commands on nodes
