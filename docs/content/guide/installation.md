# Installation

<div class="alert alert-info">You may need to install <strong>pip</strong> first. This can be accomplished through your distribution's package manager, e.g.:

<pre><code class="nohighlight">aptitude install python-pip</code></pre>

or the <a href="http://www.pip-installer.org/en/latest/installing.html">manual instructions</a>.</div>

## Using pip

It's as simple as:

<pre><code class="nohighlight">pip install bundlewrap</code></pre>

Note that you need at least Python 2.7 to run BundleWrap. Python 3 is supported as long as it's >= 3.3.

<br>

## From git

<div class="alert alert-warning">This type of install will give you the very latest (and thus possibly broken) bleeding edge version of BundleWrap.
You should only use this if you know what you're doing.</div>

<div class="alert alert-info">The instructions below are for installing on Ubuntu Server 12.10 (Quantal), but should also work for other versions of Ubuntu/Debian. If you're on some other distro, you will obviously have to adjust the package install commands.</div>

<div class="alert alert-info">The instructions assume you have root privileges.</div>

Install basic requirements:

<pre><code class="nohighlight">aptitude install build-essential git python-dev python-pip</code></pre>

Clone the GitHub repository:

<pre><code class="nohighlight">cd /opt
git clone https://github.com/bundlewrap/bundlewrap.git</code></pre>

Use `pip install -e` to install in "development mode":

<pre><code class="nohighlight">pip install -e /opt/bundlewrap</code></pre>

You can now try running the `bw` command line utility:

<pre><code class="nohighlight">bw --help</code></pre>

That's it.

To update your install, just pull the git repository and have setup.py` check for new dependencies:

<pre><code class="nohighlight">cd /opt/bundlewrap
git pull
python setup.py develop</code></pre>

<br>

# Requirements for managed systems

While the following list might appear long, even very minimal systems should provide everything that's needed.

* `apt-get` (only used with [pkg_apt](../items/pkg_apt.md) items)
* `cat`
* `chmod`
* `chown`
* `dpkg` (only used with [pkg_apt](../items/pkg_apt.md) items)
* `echo`
* `file`
* `find`
* `grep`
* `groupadd`
* `groupmod`
* `id`
* `initctl` (only used with [svc_upstart](../items/svc_upstart.md) items)
* `mkdir`
* `mv`
* `pacman` (only used with [pkg_pacman](../items/pkg_pacman.md) items)
* `rm`
* sftp-enabled SSH server (your home directory must be writable)
* `sudo`
* `sha1sum`
* `stat`
* `systemctl` (only used with [svc_systemd](../items/svc_systemd.md) items)
* `tar` (only used with [git_deploy](../items/git_deploy.md) items)
* `useradd`
* `usermod`

Additionally, you need to pre-configure your SSH client so that it can connect to your nodes without having to type a password (including `sudo` on the node, which also must *not* have the `requiretty` option set).
