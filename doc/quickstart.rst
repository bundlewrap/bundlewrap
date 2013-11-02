.. _quickstart:

Quickstart
==========

This is the 5 minute intro into Blockwart. Fasten your seatbelt.

First, open a terminal and install Blockwart::

	pip install blockwart

Now you'll need to create your repository::

	mkdir my_blockwart_repo
	cd my_blockwart_repo
	bw repo create

You will note that some files have been created. Let's check them out::

	cat nodes.py
	cat groups.py

The contents should be fairly self-explanatory, but you can always check the docs on these files if you want to go deeper.

.. seealso:: :ref:`nodespy`
.. seealso:: :ref:`groupspy`

At this point you will want to edit ``nodes.py`` and maybe change "localhost" to the hostname of a system you have passwordless SSH access to. Uncomment and edit the ``ssh_username`` attribute if your local username and the one on the remote machine do not match.

The first thing you can do is run a command on your army of one node::

	bw run node1 "uptime"

Instead of a node name ("node1" in this case) you can also use a group name (such as "all") from your ``groups.py``.
