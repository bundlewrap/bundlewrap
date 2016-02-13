.. _install:

Installation
============

.. toctree::

.. hint::
   You may need to install **pip** first. This can be accomplished through your distribution's package manager, e.g.:

   ``aptitude install python-pip``

   or the `manual instructions <http://www.pip-installer.org/en/latest/installing.html>`_.

Using `pip`
-----------

It's as simple as::

    pip install bundlewrap

Note that you need at least Python 2.7 to run BundleWrap. Python 3 is supported as long as it's >= 3.3.

|

From git
--------

.. warning::
    This type of install will give you the very latest (and thus possibly broken) bleeding edge version of BundleWrap.
    You should only use this if you know what you're doing.

.. note::
    The instructions below are for installing on Ubuntu Server 12.10 (Quantal), but should also work for other versions of Ubuntu/Debian. If you're on some other distro, you will obviously have to adjust the package install commands.

.. note::
    The instructions assume you have root privileges.

Install basic requirements::

    aptitude install build-essential git python-dev python-pip

Clone the GitHub repository::

    cd /opt
    git clone https://github.com/bundlewrap/bundlewrap.git

Use ``pip install -e`` to install in "development mode"::

    pip install -e /opt/bundlewrap

You can now try running the ``bw`` command line utility::

    bw --help

That's it.

To update your install, just pull the git repository and have :file:`setup.py` check for new dependencies::

    cd /opt/bundlewrap
    git pull
    python setup.py develop
