===
FAQ
===

Technical
#########

BundleWrap says an item failed to apply, what do I do now?
---------------------------------------------------------

Try running :command:`bw apply -i nodename` to see which attribute of the item could not be fixed. If that doesn't tell you enough, try ``bw --debug apply -i nodename`` and look for the command BundleWrap is using to fix the :term:`item` in question. Then try running that command yourself and check for any errors.

|

What happens when two people start applying configuration to the same node?
---------------------------------------------------------------------------

BundleWrap uses a locking mechanism to prevent collisions like this. When BundleWrap finds a lock on a :term:`node` in interactive mode, it will display information about who acquired the lock (and when) and will ask whether to ignore the lock or abort the process. In noninteractive mode, the operation is always cancelled for the node in question unless :option:`--force` is used.

|

How can I have BundleWrap reload my services after config changes?
-----------------------------------------------------------------

See :ref:`canned actions <canned_actions>` and :ref:`triggers <triggers>`.

|

Will BundleWrap keep track of package updates?
---------------------------------------------

No. BundleWrap will only care about whether a package is installed or not. Updates will have to be installed through a separate mechanism (I like to create an :doc:`action <item_action>` with the ``interactive`` attribute set to ``True``). Selecting specific versions should be done through your package manager.

|

Is there a probing mechanism like Ohai?
---------------------------------------

No. BundleWrap is meant to be very push-focused. The node should not have any say in what configuration it will receive. If you disagree with this ideology and really need data from the node beforehand, you can use a :ref:`hook <hooks>` to gather the data and populate ``node.metadata``.

|

Is there a way to remove any unmanaged files/directories in a directory?
------------------------------------------------------------------------

Not at the moment. We're tracking this topic in issue `#56 <https://github.com/bundlewrap/bundlewrap/issues/56>`_.

|

Is there any integration with my favorite Cloud?
------------------------------------------------

Not right now. A separate project (called "cloudwart") is in planning, but no code has been written and it's not a priority at the moment.

|

Is BundleWrap secure?
--------------------

BundleWrap is more concerned with safety than security. Due to its design, it is possible for your coworkers to introduce malicious code into a BundleWrap repository that could compromise your machine. You should only use trusted repositories and plugins. We also recommend following commit logs to your repos.

|

The BundleWrap Project
#####################

Why do contributors have to sign a Copyright Assignment Agreement?
------------------------------------------------------------------

While it sounds scary, Copyright assignment is used to improve the enforceability of the GPL. Even the FSF does it, `read their explanation why <http://www.gnu.org/licenses/why-assign.html>`_. The agreement used by BundleWrap is from `harmonyagreements.org <http://harmonyagreements.org>`_.

If you're still concerned, please do not hesitate to contact `@trehn <https://twitter.com/trehn>`_.

|
