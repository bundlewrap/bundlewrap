Requirements for managed systems
================================

While the following list might appear long, even very minimal systems should provide everything that's needed.

* ``apt-cache`` (only used with ``packages_debian``)
* ``apt-get`` (only used with ``packages_debian``)
* ``cat``
* ``chmod``
* ``chown``
* ``dpkg`` (only used with ``packages_debian``)
* ``echo``
* ``export``
* ``file``
* ``grep``
* ``mkdir``
* ``mv``
* ``rm``
* ``sed``
* ``test``
* sftp-enabled SSH server (only used with remotely managed systems)
* ``sudo`` (access to all other commands listed here, without password)
* depending on the configured ``hashmethod`` setting, at least one of: ``md5sum``, ``sha1sum``, ``sha224sum``, ``sha256sum``, ``sha384sum``, ``sha512sum``