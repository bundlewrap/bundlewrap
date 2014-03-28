===
FAQ
===

Technical
#########

What happens when two people start applying configuration to the same node?
---------------------------------------------------------------------------

Blockwart uses a locking mechanism to prevent collisions like this. When Blockwart finds a lock on a node in interactive mode, it will display information about who acquired the lock (and when) and will ask whether to ignore the lock or abort the process. In noninteractive mode, the operation is always cancelled for the node in question unless :option:`--force` is used.

|

How can I have Blockwart reload my services after config changes?
-----------------------------------------------------------------

See :ref:`canned actions <canned_actions>` and :ref:`triggers <triggers>`.

|

Will Blockwart keep track of package updates?
---------------------------------------------

No. Blockwart will only care about whether a package is installed or not. Updates will have to be installed through a separate mechanism (I like to create an action with the ``interactive`` attribute set to ``True``). Selecting specific version should be done through your package manager.

|

Is there a probing mechanism like Ohai?
---------------------------------------

No. Blockwart is meant to be very push-focused. The node should not have any say in that configuration it will receive. If you disagree with this ideology and really need data from the node beforehand, you can use a :ref:`hook <hooks>` to gather the data and populate ``node.metadata``.

|

Is there a way to remove any unmanaged files/directories in a directory?
------------------------------------------------------------------------

Not at the moment. We're tracking this topic in issue `#56 <https://github.com/trehn/blockwart/issues/56>`_.

|

Is there any integration with my favorite Cloud?
------------------------------------------------

Not right now. A separate project (called "cloudwart") is in planning, but no code has been written and it's not a priority at the moment.

|

The Blockwart Project
#####################

Why do contributors have to sign a Copyright Assignment Agreement?
------------------------------------------------------------------

While it sounds scary, Copyright assignment is used to improve the enforcability of the GPL. Even the FSF does it, `read their explanation why <http://www.gnu.org/licenses/why-assign.html>`_. The agreement used by Blockwart is from `harmonyagreements.org <http://harmonyagreements.org>`_.

If you're still concerned, please do not hesitate to contact `@trehn <https://twitter.com/trehn>`_.

|

Isn't the name evil?
--------------------

The origins of the name "Blockwart" are described on the :doc:`about` page. We have heard concerns from several people about using a Nazi term to describe our project.

	I do not believe I chose the wrong name for this project. The theme fits perfectly and there is nothing discriminatory and inherently evil about using the word "Blockwart", especially considering its use in modern German (which could very well exist without the Nazi origins). Putting words on a blacklist is not going to solve anything. So far, the name has sparked many interesting discussions and debate. I like that.

	-- Torsten Rehn

Nonetheless, let it be clear that the Blockwart project does not support or condone fascism (except for when it comes to grammar and coding style). We welcome anyone to be part of our community.
