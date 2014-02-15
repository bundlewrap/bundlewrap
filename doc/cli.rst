.. _cli:

###
CLI
###

The ``bw`` utility is Blockwart's command line interface.

.. note::

	This page is not meant as a complete reference. It provides a starting point to explore the various subcommands. If you're looking for details, ``--help`` is your friend.

|

``bw apply``
------------

.. code-block:: console

	$ bw apply -i mynode

The most important and most used part of Blockwart, ``bw apply`` will apply your configuration to a set of nodes. By default, it operates in a non-interactive mode. When you're trying something new or are otherwise unsure of some changes, use the ``-i`` switch to have Blockwart interactively ask before each change is made.

|

``bw run``
------------

.. code-block:: console

	$ bw run mygroup "uname -a"

Unsurprisingly, the ``run`` subcommand is used to run commands on nodes. As with most commands that accept node names, you can also give a group name or any combination of node and group names, separated by commas (without spaces, e.g. ``node1,group2,node3``).

|

``bw nodes`` and ``bw groups``
------------------------------

.. code-block:: console

	$ bw nodes --hostnames | xargs -n 1 ping -c 1

With these commands you can quickly get a list of all nodes and groups in your repository. The example above uses ``--hostnames`` to get a list of all DNS names for your nodes and send a ping to each one.

|

``bw repo debug``
-----------------

.. code-block:: pycon

	$ bw repo debug
	blockwart X.Y.Z interactive repository inspector
	> You can access the current repository as 'repo'.
	>>> len(repo.nodes)
	121

This command will drop you into a Python shell with direct access to Blockwart's :doc:`API <api>`. Once you're familiar with it, it can be a very powerful tool.

|

``bw repo plot``
----------------

.. hint:: You'll need `Graphviz <http://www.graphviz.org/>`_ installed on your machine for this to be useful.

.. code-block:: console

	$ bw repo plot mynode | dot -Tsvg -omynode.svg

You won't be using this every day, but it's pretty cool. The above command will create an SVG file (you can open these in your browser) that shows the item dependency graph for the given node. You will see bundles as dashed rectangles, static dependencies (defined in Blockwart itself) in green, auto-generated dependencies (calculated dynamically each time you run ``bw apply``) in blue and dependencies you defined yourself in red.

It offers an interesting view into the internal complexities Blockwart has to deal with when figuring out the order in which your items can be applied to your node.
