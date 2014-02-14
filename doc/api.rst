.. _api:

===
API
===

.. toctree::

While most users will interact with Blockwart through the ``bw`` command line utility, you can also use it from your own code to extract data or further automate config management tasks.

Even within Blockwart itself (e.g. templates, libs, and hooks) your are often given repo and/or node objects to work with. Their methods and attributes are documented below.


Example
#######

Here's a short example of how to use Blockwart to get the uptime for a node.

.. code-block:: python

	from blockwart.repo import Repository

	repo = Repository("/path/to/my/repo")
	node = repo.get_node("mynode")
	uptime = node.run("uptime")
	print(uptime.stdout)


Reference
#########

.. py:module:: blockwart.repo

.. py:class:: Repository(path)

	The starting point of any interaction with Blockwart. An object of this class represents the repository at the given path.

	.. py:method:: get_node(node_name)

		Get the node object with the given name.

		:param str node_name: Name of the desired node
		:return: The node object for the given name
		:rtype: Node


.. py:module:: blockwart.node

.. py:class:: Node()

	A system managed by Blockwart.

	.. py:method:: download(remote_path, local_path)

		Downloads a file from the node.

		:param str remote_path: Which file to get from the node
		:param str local_path: Where to put the file

	.. py:method:: run(command, may_fail=False)

		Runs a command on the node.

		:param str command: What should be executed on the node
		:param bool may_fail: If ``False``, :py:exc:`blockwart.exceptions.RemoteException` will be raised if the command does not return 0.
		:return: The node object for the given name
		:rtype: Node
