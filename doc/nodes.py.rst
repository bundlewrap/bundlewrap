.. _nodespy:

##################
nodes.py reference
##################

.. toctree::
    :hidden:

This file lets you specify or dynamically build a list of nodes in your environment.

Introduction
============

All you have to do here is define a Python dictionary called ``nodes``. It should look something like this::

	nodes = {
		'node1': {
			'hostname': "node1.example.com",
		},
	}



.. note::
	With blockwart, the DNS name and the internal identifier for a node are two separate things. This allows for clean and sortable hierarchies::

		nodes = {
			'cluster1.node1': {
				'hostname': "node1.cluster1.example.com",
			},
		}



All fields for a node (including ``hostname``) are optional. If you don't give one, blockwart will attempt to use the internal identifier to connect to a node::

	nodes = {
		'node1.example.com': {},
	}

Dynamic node list
=================

You are not confined to the static way of defining a node list as shown above. You can also assemble the ``nodes`` dictionary dynamically::

	def get_my_nodes_from_ldap():
	    [...]
	    return ldap_nodes

	nodes = get_my_nodes_from_ldap()

Node attribute reference
========================

This section is a reference for all possible attributes you can define for a node::

	nodes = {
		'node1': {
			# THIS PART IS EXPLAINED HERE
		},
	}

``hostname``
------------

A string used as a DNS name when connecting to this node. May also be an IP address.
