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

A dictionary of arbitrary data that will be accessible from each node's ``node.metadata``. For each node, BundleWrap will merge the metadata of all of the node's groups first, then merge in the metadata from the node itself.

.. warning::

	Be careful when defining conflicting metadata (i.e. dictionaries that have some common keys) in multiple groups. BundleWrap will consider group hierarchy when merging metadata. For example, it is possible to define a default nameserver for the "eu" group and then override it for the "eu.frankfurt" subgroup. The catch is that this only works for groups that are connected through a subgroup hierarchy. Independent groups will have their metadata merged in an undefined order.

|

``metadata_processors``
-----------------------

.. note::

	This is an advanced feature. You should already be very familiar with BundleWrap before using this.

A list of strings formatted as ``module.function`` where *module* is the name of a file in the ``libs/`` :doc:`subdirectory <libs>` of your repo (without the ``.py`` extension) and *function* is the name of a function in that file.

This function can be used to dynamically manipulate metadata after the static metadata has been generated. It looks like this:

.. code-block:: python

	def example1(node_name, groups, metadata, **kwargs):
	    if "group1" in groups and "group2" in groups:
	        metadata['foo'].append("bar")
	    return metadata

As you can see, the metadata processor function is passed the node name, a list of group names and the metadata dictionary generated so far. You can then manipulate that dictionary based on these parameters and must return the modified metadata dictionary.

|

``subgroups``
-------------

A tuple or list of group names whose members should be recursively included in this group.
