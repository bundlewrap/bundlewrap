.. _quickstart:

Quickstart
==========

.. toctree::

This is the 10 minute intro into BundleWrap. Fasten your seatbelt.

|

Installation
------------

First, open a terminal and install BundleWrap::

	pip install bundlewrap

|

Create a repository
-------------------

Now you'll need to create your :term:`repository <repo>`::

	mkdir my_bundlewrap_repo
	cd my_bundlewrap_repo
	bw repo create

You will note that some files have been created. Let's check them out::

	cat nodes.py
	cat groups.py

The contents should be fairly self-explanatory, but you can always check the :doc:`docs <repository>` on these files if you want to go deeper.

.. hint::

	It is highly recommended to use git or another :abbr:`SCM (Source Code Management)` tool to keep track of your repository. You may want to start doing that right away.

At this point you will want to edit :file:`nodes.py` and maybe change "localhost" to the hostname of a system you have passwordless (including sudo) SSH access to.

.. note::

	BundleWrap will honor your ``~/.ssh/config``, so if ``ssh mynode.example.com sudo id`` works without any password prompts in your terminal, you're good to go.

	If you need a password for SSH and/or sudo, please add :option:`-p` directly after :command:`bw` when calling :command:`bw run` or :command:`bw apply`.

|

Run a command
-------------

The first thing you can do is run a command on your army of one :term:`node`::

	bw run node1 "uptime"

You should see something like this::

	[node1] out:  17:23:19 up 97 days,  2:51,  2 users,  load average: 0.08, 0.03, 0.05
	[node1] out:
	[node1] ✓ completed successfully after 1.18188s

Instead of a node name ("node1" in this case) you can also use a :term:`group` name (such as "all") from your ``groups.py``.

|

Create a bundle
---------------

BundleWrap stores node configuration in :term:`bundles <bundle>`. A bundle is a collection of :term:`items <item>` such as files, system packages or users. To create your first bundle, type::

	bw repo bundle create mybundle

Now that you have created your bundle, it's important to tell BundleWrap which nodes will have this bundle. You can assign bundles to nodes using either :file:`groups.py` or :file:`nodes.py`, here we'll use the latter:

.. code-block:: python

	nodes = {
	    'node1': {
	        'bundles': (
	            "mybundle",
	        ),
	        'hostname': "mynode1.local",
	    },
	}

|

Create a file template
----------------------

To manage a file, you need two things:

	1. a file item in your bundle
	2. a template for the file contents

Add this to your :file:`bundles/mybundle/bundle.py`:

.. code-block:: python

	files = {
	    '/etc/motd': {
	        'source': "etc/motd",
	    },
	}

Then write the file template::

	mkdir bundles/mybundle/files/etc
	vim bundles/mybundle/files/etc/motd

You can use this for example content::

	Welcome to ${node.name}!

Note that the "source" attribute in :file:`bundle.py` contains a path relative to the :file:`files` directory of your bundle. It's up to you how to organize the contents of this directory.

|

Apply configuration
-------------------

Now all that's left is to run :command:`bw apply`::

	bw apply -i node1

BundleWrap will ask to replace your previous :abbr:`MOTD (message of the day)`::

	node1: run started at 2013-11-16 18:26:29

	 ╭  file:/etc/motd
	 ┃
	 ┃   content
	 ┃   --- /etc/motd
	 ┃   +++ <bundlewrap content>
	 ┃   @@ -1 +1 @@
	 ┃   -your old motd
	 ┃   +Welcome to node1!
	 ┃
	 ╰  Fix file:/etc/motd? [Y/n]

That completes the quickstart tutorial!

|

Further reading
---------------

Here are some suggestions on what to do next:

* take a moment to think about what groups and bundles you will create
* read up on how a :doc:`BundleWrap repository <repository>` is laid out
* ...especially what types of items you can add to your :doc:`bundles <bundles>`
* familiarize yourself with `the Mako template language <http://www.makotemplates.org/>`_
* explore the :doc:`command line interface <cli>`
* follow `@bwapply <https://twitter.com/bwapply>`_ on Twitter

Have fun! If you have any questions, feel free to drop by `on IRC <irc://chat.freenode.net/bundlewrap>`_.
