.. _cli:

######################
Command Line Interface
######################

The :command:`bw` utility is Blockwart's command line interface.

.. note::

	This page is not meant as a complete reference. It provides a starting point to explore the various subcommands. If you're looking for details, :option:`--help` is your friend.

|

``bw apply``
------------

.. code-block:: console

	$ bw apply -i mynode

The most important and most used part of Blockwart, :command:`bw apply` will apply your configuration to a set of :term:`nodes <node>`. By default, it operates in a non-interactive mode. When you're trying something new or are otherwise unsure of some changes, use the :option:`-i` switch to have Blockwart interactively ask before each change is made.

|

``bw run``
------------

.. code-block:: console

	$ bw run mygroup "uname -a"

Unsurprisingly, the ``run`` subcommand is used to run commands on nodes.

|

As with most commands that accept node names, you can also give a :term:`group` name or any combination of node and group names, separated by commas (without spaces, e.g. ``node1,group2,node3``). A third option is to use a bundle selector like ``bundle:my_bundle``. It will select all nodes with the named :term:`bundle`. You can freely mix and match node names, group names, and bundle selectors.

|

Negation is also possible for bundles and groups. ``!bundle:foo`` will add all nodes without the foo bundle, while ``!group:foo`` will add all nodes that aren't in the foo group.

|

``bw nodes`` and ``bw groups``
------------------------------

.. code-block:: console

	$ bw nodes --hostnames | xargs -n 1 ping -c 1

With these commands you can quickly get a list of all nodes and groups in your :term:`repository`. The example above uses :option:`--hostnames` to get a list of all DNS names for your nodes and send a ping to each one.

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

You won't be using this every day, but it's pretty cool. The above command will create an SVG file (you can open these in your browser) that shows the item dependency graph for the given node. You will see bundles as dashed rectangles, static dependencies (defined in Blockwart itself) in green, auto-generated dependencies (calculated dynamically each time you run :command:`bw apply`) in blue and dependencies you defined yourself in red.

It offers an interesting view into the internal complexities Blockwart has to deal with when figuring out the order in which your items can be applied to your node.

|

``bw repo test``
----------------

.. code-block:: console

	$ bw repo test
	✓ node1:pkg_apt:samba
	✘ node1:file:/etc/samba/smb.conf

	[...]

	+----- traceback from worker ------
	|
	|  Traceback (most recent call last):
	|    File "/Users/trehn/Projects/software/blockwart/src/blockwart/concurrency.py", line 78, in _worker_process
	|      return_value = target(*msg['args'], **msg['kwargs'])
	|    File "<string>", line 378, in test
	|  BundleError: file:/etc/samba/smb.conf from bundle 'samba' refers to missing file '/path/to/blockwart/repo/bundles/samba/files/smb.conf'
	|
	+----------------------------------

This command is meant to be run automatically like a test suite after every commit. It will try to catch any errors in your bundles and file templates by initializing every item for every node (but without touching the network).
