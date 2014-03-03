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

|

Reference
#########

|

.. py:module:: blockwart.repo

.. py:class:: Repository(path)

	The starting point of any interaction with Blockwart. An object of this class represents the repository at the given path.

	.. py:attribute:: groups

		A list of all groups in the repo (instances of :py:class:`blockwart.group.Group`)

	.. py:attribute:: group_names

		A list of all group names in this repo.

	.. py:attribute:: nodes

		A list of all nodes in the repo (instances of :py:class:`blockwart.node.Node`)

	.. py:attribute:: node_names

		A list of all node names in this repo

	.. py:attribute:: revision

		The current git, hg or bzr revision of this repo. ``None`` if no SCM was detected.

	|

	.. py:method:: get_group(group_name)

		Get the group object with the given name.

		:param str group_name: Name of the desired group
		:return: The group object for the given name
		:rtype: :py:class:`blockwart.group.Group`

	|

	.. py:method:: get_node(node_name)

		Get the node object with the given name.

		:param str node_name: Name of the desired node
		:return: The node object for the given name
		:rtype: :py:class:`blockwart.node.Node`


|
|

.. py:module:: blockwart.node

.. py:class:: Node()

	A system managed by Blockwart.

	.. py:attribute:: bundles

		A list of all bundles associated with this node (instances of :py:class:`blockwart.bundle.Bundle`)

	.. py:attribute:: groups

		A list of :py:class:`blockwart.group.Group` objects this node belongs to

	.. py:attribute:: hostname

		The DNS name Blockwart uses to connect to this node

	.. py:attribute:: metadata

		A dictionary of custom metadata as defined in :doc:`nodes.py <nodes.py>`

	.. py:attribute:: name

		The internal identifier for this node

	|

	.. py:method:: download(remote_path, local_path)

		Downloads a file from the node.

		:param str remote_path: Which file to get from the node
		:param str local_path: Where to put the file

	|

	.. py:method:: has_bundle(bundle_name)

		``True`` if the node has a bundle with the given name.

		:param str bundle_name: Name of the bundle to look for
		:rtype: bool

	|

	.. py:method:: has_any_bundle(bundle_names)

		``True`` if the node has a bundle with any of the given names.

		:param list bundle_names: List of bundle names to look for
		:rtype: bool

	|

	.. py:method:: in_group(group_name)

		``True`` if the node is in a group with the given name.

		:param str group_name: Name of the group to look for
		:rtype: bool

	|

	.. py:method:: in_any_group(group_names)

		``True`` if the node is in a group with any of the given names.

		:param list group_names: List of group names to look for
		:rtype: bool

	|

	.. py:method:: run(command, may_fail=False)

		Runs a command on the node.

		:param str command: What should be executed on the node
		:param bool may_fail: If ``False``, :py:exc:`blockwart.exceptions.RemoteException` will be raised if the command does not return 0.
		:return: An object that holds the return code as well as captured stdout and stderr
		:rtype: :py:class:`blockwart.operations.RunResult`

	|

	.. py:method:: upload(local_path, remote_path, mode=None, owner="", group="")

		Uploads a file to the node.

		:param str local_path: Which file to upload
		:param str remote_path: Where to put the file on the target node
		:param str mode: File mode, e.g. "0644"
		:param str owner: Username of the file owner
		:param str group: Group name of the file group

|
|

.. py:module:: blockwart.group

.. py:class:: Group

	A user-defined group of nodes.

	.. py:attribute:: name

		The name of this group

	.. py:attribute:: nodes

		A list of all nodes in this group (instances of :py:class:`blockwart.node.Node`, includes subgroup members)


|
|

Dragons
#######

If you're a little more daring, you can construct "virtual" repositories entirely in memory.

.. warning::

	This is considered pretty experimental.

.. code-block:: python

	from blockwart.bundle import Bundle
	from blockwart.node import Node
	from blockwart.repo import Repository

	repo = Repository()
	node = Node("mynode", {'hostname': "mynode.example.com"})
	repo.add_node(node)
	bundle = node.add_bundle("mybundle")
	bundle.add_item("files", "/tmp/CLOUD", {'content': "BIGDATA"})
	result = node.apply()
