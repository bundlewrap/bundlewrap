.. _nodespy:

########
nodes.py
########

.. toctree::
    :hidden:

This file lets you specify or dynamically build a list of nodes in your environment.

|

Introduction
============

All you have to do here is define a Python dictionary called ``nodes``. It should look something like this:

.. code-block:: python

	nodes = {
	    'node1': {
	        'hostname': "node1.example.com",
	    },
	}



.. note::
	With BundleWrap, the DNS name and the internal identifier for a node are two separate things. This allows for clean and sortable hierarchies:

	.. code-block:: python

		nodes = {
		    'cluster1.node1': {
		        'hostname': "node1.cluster1.example.com",
		    },
		}



All fields for a node (including ``hostname``) are optional. If you don't give one, BundleWrap will attempt to use the internal identifier to connect to a node:

.. code-block:: python

	nodes = {
	    'node1.example.com': {},
	}

|

Dynamic node list
=================

You are not confined to the static way of defining a node list as shown above. You can also assemble the ``nodes`` dictionary dynamically:

.. code-block:: python

	def get_my_nodes_from_ldap():
	    [...]
	    return ldap_nodes

	nodes = get_my_nodes_from_ldap()

|

Node attribute reference
========================

This section is a reference for all possible attributes you can define for a node:

.. code-block:: python

	nodes = {
	    'node1': {
	        # THIS PART IS EXPLAINED HERE
	    },
	}

``bundles``
-----------

A list of :doc:`bundles <bundles>` to be assigned to this node.

|

``hostname``
------------

A string used as a DNS name when connecting to this node. May also be an IP address.

.. note::
   The username and SSH private key for connecting to the node cannot be configured in BundleWrap. If you need to customize those, BundleWrap will honor your ``~/.ssh/config``.

|

``metadata``
------------

This can be a dictionary of arbitrary data. You can access it from your templates as ``node.metadata``. Use this to attach custom data (such as a list of IP addresses that should be configured on the target node) to the node. Note that you can also define metadata at the :ref:`group level <item_group>`, but node metadata has higher priority.

|

``use_shadow_passwords``
------------------------

.. warning::
   Changing this setting will affect the security of the target system. Only do this for legacy systems that don't support shadow passwords.

This setting will affect how the :doc:`user <item_user>` item operates. If set to ``False``, password hashes will be written directly to ``/etc/passwd`` and thus be accessible to any user on the system.
