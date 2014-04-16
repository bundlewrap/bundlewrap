.. _groupspy:

#########
groups.py
#########

.. toctree::
    :hidden:

This file lets you specify or dynamically build a list of groups in your environment.

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

A dictionary of arbitrary data that will be accessible from each node's ``node.metadata``. For each node, Blockwart will merge the metadata of all of the node's groups first, then merge in the metadata from the node itself. You should not put conflicting metadata (i.e. dicts that share keys) in groups because there is no control over which group's metadata will be merged in last. You can, of course, put some metadata in a group and then default override it at the node level.

|

``subgroups``
-------------

A tuple or list of group names whose members should be recursively included in this group.
