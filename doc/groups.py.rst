.. _groupspy:

###################
groups.py reference
###################

.. toctree::
    :hidden:

This file lets you specify or dynamically build a list of groups in your environment.

Introduction
============

As with ``nodes.py``, you define your groups as a dictionary::

	groups = {
		'group1': {
			'members': (
				'node1',
			),
		},
	}

All fields for a group are optional.

Group attribute reference
=========================

This section is a reference for all possible attributes you can define for a group::

	groups = {
		'group1': {
			# THIS PART IS EXPLAINED HERE
		},
	}

``members``
-----------

A tuple or list of node names that belong to this group.

``subgroups``
-------------

A tuple or list of group names whose members should be recursively included in this group.

Group patterns
==============

You may want to define an aditional dictionary called ``group_patterns`` that maps regular expressions to group names::

	group_patterns = {
		r".*": "all",
		r"^cluster1\.": "cluster1",
		r"(.+\.)?app\d+": "appservers",
	}

Node names will be matched against these regexes and placed into groups accordingly. In the above example, a node named "cluster1.app03" would be added to the groups "all", "cluster1" and "appservers".
