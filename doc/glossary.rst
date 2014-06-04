########
Glossary
########


.. glossary::

	action
		Actions are a special kind of :term:`item` used for running shell commands during each :command:`bw apply`. They allow you to do things that aren't persistent in nature

	apply
		An "apply" is what we call the process of what's otherwise known as "converging" the state described by your repository and the actual status quo on the :term:`node`.

	bundle
		A collection of :term:`items <item>`. Most of the time, you will create one bundle per application. For example, an Apache bundle will include the httpd service, the virtual host definitions and the apache2 package.

	group
		Used for organizing your :term:`nodes <node>`.

	hook
		:doc:`Hooks <hooks>` can be used to run your own code automatically during various stages of Blockwart operations.

	item
		A single piece of configuration on a node, e.g. a file or an installed package.

		You might be interested in :ref:`this overview of item types <item_types>`.

	lib
		:doc:`Libs <libs>` are a way to store Python modules in your repository and make them accessible to your bundles and templates.

	node
		A managed system, no matter if physical or virtual.

	repo
		A repository is a directory with :doc:`some stuff <repository>` in it that tells Blockwart everything it needs to know about your infrastructure.
