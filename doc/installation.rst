.. _install:

Installation
============

.. hint::
   You may need to install **pip** first. This can be accomplished through your distribution's package manager, e.g.:

   ``aptitude install python-pip``

   or the `manual instructions <http://www.pip-installer.org/en/latest/installing.html>`_.

Using `pip`
-----------

It's as simple as::

    pip install blockwart

From git
--------

.. warning::
    This type of install will give you the very latest (and thus possibly broken) bleeding edge version of blockwart.
    You should only use this if you know what you're doing.

.. note::
    The instructions below are for installing on Ubuntu Server 12.10 (Quantal), but should also work for other versions of Ubuntu/Debian. If you're on some other distro, you will obviously have to adjust the package install commands.

.. note::
    The instructions assume you have root privileges.

Install basic requirements::

    aptitude install build-essential git python-dev python-distribute

Clone the GitHub repository::

    cd /opt
    git clone https://github.com/trehn/blockwart.git

Use ``setup.py`` to install in "development mode"::

    cd /opt/blockwart
    python setup.py develop

You can now try running the ``bw`` command line utility::

    bw --help

That's it.

To update your install, just pull the git repository and have ``setup.py`` check for new dependencies::

    cd /opt/blockwart
    git pull
    python setup.py develop
