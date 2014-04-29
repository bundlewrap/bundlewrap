.. _groupspy:

#########
groups.py
#########

.. toctree::
    :hidden:

This file lets you specify or dynamically build a list of :term:`groups <group>` in your environment.

Introduction
============

As with :file:`nodes.py`, you define your groups as a dictionary:

.. code-block:: python

	groups = {
	    'all': {
	        'member_patterns': (
	            r".*",
	        ),
	    },
	    'group1': {
	        'members': (
	            'node1',
	        ),
	    },
	}

All group attributes are optional.

|

Group attribute reference
=========================

This section is a reference for all possible attributes you can define for a group:

.. code-block:: python

	groups = {
	     'group1': {
	         # THIS PART IS EXPLAINED HERE
	     },
	}

``bundles``
-----------

A list of :doc:`bundles <bundles>` to be assigned to each node in this group.

|

``member_patterns``
-------------------

A list of regular expressions. Node names matching these expressions will be added to the group members.

Matches are determined using `the search() method <http://docs.python.org/2/library/re.html#re.RegexObject.search>`_.

|

``members``
-----------

A tuple or list of node names that belong to this group.

|

``metadata``
------------

A dictionary of arbitrary data that will be accessible from each node's ``node.metadata``. For each node, Blockwart will merge the metadata of all of the node's groups first, then merge in the metadata from the node itself.

.. warning::

	Be careful when defining conflicting metadata (i.e. dictionaries that have some common keys) in multiple groups. Blockwart will consider group hierarchy when merging metadata. For example, it is possible to define a default nameserver for the "eu" group and then override it for the "eu.frankfurt" subgroup. The catch is that this only works for groups that are connected through a subgroup hierarchy. Independent groups will have their metadata merged in an undefined order.

|

``subgroups``
-------------

A tuple or list of group names whose members should be recursively included in this group.
