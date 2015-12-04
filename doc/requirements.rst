Requirements for managed systems
================================

.. toctree::

While the following list might appear long, even very minimal systems should provide everything that's needed.

* :command:`apt-get` (only used with :doc:`pkg_apt <item_pkg_apt>` items)
* :command:`base64`
* :command:`bash`
* :command:`cat`
* :command:`chmod`
* :command:`chown`
* :command:`dpkg` (only used with :doc:`pkg_apt <item_pkg_apt>` items)
* :command:`echo`
* :command:`export`
* :command:`file`
* :command:`grep`
* :command:`groupadd`
* :command:`groupmod`
* :command:`id`
* :command:`initctl` (only used with :doc:`svc_upstart <item_svc_upstart>` items)
* :command:`mkdir`
* :command:`mv`
* :command:`pkgin` (only used with :doc:`pkg_pkgsrc <item_pkg_pkgsrc>` items)
* :command:`pacman` (only used with :doc:`pkg_pacman <item_pkg_pacman>` items)
* :command:`rm`
* :command:`sed`
* sftp-enabled SSH server (your home directory must be writable)
* :command:`sudo`
* :command:`sha1sum`
* :command:`svcadm` (only used with :doc:`svc_smf <item_svc_smf>` items)
* :command:`svcs` (only used with :doc:`svc_smf <item_svc_smf>` items)
* :command:`systemctl` (only used with :doc:`svc_systemd <item_svc_systemd>` items)
* :command:`test`
* :command:`useradd`
* :command:`usermod`
