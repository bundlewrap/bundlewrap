######################
Writing file templates
######################

Blockwart uses `Mako <http://www.makotemplates.org>`_ for file templating. This enabled you to dynamically contruct your config files.

The most basic example would be::

	Hello, this is ${node.name}!

After template rendering, it would look like this::

	Hello, this is myexamplenodename!

As you can see, `${...}` can be used to insert the value of a context variable into the rendered file. By default, you have access to two variables in every template: `node` and `repo`. They are :class:`blockwart.node.Node` and :class:`blockwart.repo.Repository` objects, respectively. You can learn more about the attributes and methods of these objects :doc:`in the API docs <api>`, but here are a few examples:

|

inserts the DNS hostname of the current node

.. code-block:: python

	${node.hostname}

|

a list of all nodes in your repo

.. code-block:: python

	% for node in repo.nodes:
	${node.name}
	% endfor

|

make exceptions for certain nodes

.. code-block:: python

	% if node.name == "node1":
	option = foo
	% elif node.name in ("node2", "node3"):
	option = bar
	% else:
	option = baz
	% endif

|

check for group membership

.. code-block:: python

	% if node.in_group("sparkle"):
	enable_sparkles = 1
	% endif

|

check for membership in any of several groups

.. code-block:: python

	% if node.in_any_group(("sparkle", "shiny")):
	enable_fancy = 1
	% endif

|

check for bundle

.. code-block:: python

	% if node.has_bundle("sparkle"):
	enable_sparkles = 1
	% endif

|

check for any of several bundles

.. code-block:: python

	% if node.has_any_bundle(("sparkle", "shiny")):
	enable_fancy = 1
	% endif

|

list all nodes in a group

.. code-block:: python

	% for gnode in repo.get_group("mygroup").nodes:
	${gnode.name}
	% endfor

|

Working with node metadata
--------------------------
 Quite often you will attach custom metadata to your nodes in :file:`nodes.py`, e.g.:

 .. code-block:: python

 	nodes = {
 		"node1": {
 			"metadata": {
 				"interfaces": {
 					"eth0": "10.1.1.47",
 					"eth1": "10.1.2.47",
 				},
 			},
 		},
 	}

You can easily access this information in templates:

.. code-block:: python

	% for interface, ip in node.metadata["interfaces"].items():
	interface ${interface}
		ip = ${ip}
	% endfor

This template will render to::

	interface eth0
		ip = 10.1.1.47
	interface eth1
		ip = 10.1.2.47

