Glossary
========

Abstract configuration
----------------------

This is configuration as written by users. It's the contents of bundles and templates, among other things.

Bundle
------

A piece of abstract configuration describing a series of config items that are related in some way. For example, there might be an Apache bundle that contains the 'apache2-mpm-worker' package, the '/etc/apache2/httpd.conf' file and the 'apache2' service.

Config item
-----------

A single 'thing' that is being managed on a system. Some popular examples: Files, directories, packages, services, databases.

Group
-----

A means to organize nodes into - well - groups. Groups also define a set of bundles which are applied to their members.

Literal configuration
---------------------

This is the configuration as it is transmitted to the client. There are no more moving parts (such as template logic in abstract configuration), this is just the bare info a tool needs to do its job (e.g. the contents of a file).

Node
----

Blockwart's idea of a virtual machine, a server, a piece of cloud or a toaster that runs Linux.

Metadata
--------

Information about a node, such as what architecture it runs and what profile/groups it has been assigned.
