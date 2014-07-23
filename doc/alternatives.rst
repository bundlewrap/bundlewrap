############
Alternatives
############

This page is an effort to compare BundleWrap to other config management systems. It very hard to keep this information complete and up to date, so please feel free to raise issues or create pull requests if something is amiss.

BundleWrap has the following properties that are unique to it or at least not common among other solutions:

* server- and agent-less architecture
* item-level parallelism to speed up convergence of complex nodes
* interactive mode to review configuration as it it being applied
* :doc:`Mako file templates <item_file_templates>`
* verifies that each action taken actually fixed the item in question
* useful and actionable error messages
* built-in :ref:`visualization <bw_plot>` of node configuration
* nice :doc:`Python API <api>`
* designed to be mastered quickly and easily remembered
* for better or worse: no commercial agenda/support

|

.. _ansible:

Ansible
-------

Ansible is very similar to BundleWrap in how it communicates with nodes. Both systems do not use server or agent processes, but SSH. Ansible can optionally use OpenSSH instead of a Python SSH implementation to speed up performance. On the other hand, BundleWrap will always use the Python implementation, but with multiple connections to each node. This should give BundleWrap a performance advantage on very complex systems with many items, since each connection can work on a different item simultaneously.

To apply configuration, Ansible uploads pieces of code called modules to each node and runs them there. Many Ansible modules depend on the node having a Python 2.x interpreter installed. BundleWrap runs commands on the target node just as you would in an interactive SSH session. Most of the :doc:`commands needed <requirements>` by BundleWrap are provided by coreutils and should be present on all standard Linux systems.

Ansible ships with loads of modules while BundleWrap will only give you the most needed primitives to work with. For example, we will not add an item type for remote downloads because you can easily build that yourself using an :doc:`action <item_action>` with :command:`wget`.

Ansible's playbooks roughly correspond to BundleWrap's bundles, but are written in YAML using a special playbook language. BundleWrap uses Python for this purpose, so if you know some basic Python you only need to learn the schema of the dictionaries you're building.

File templates in Ansible are `Jinja2 <http://jinja2.pocoo.org>`_, while BundleWrap uses `Mako <http://makotemplates.org>`_ by default and offers Jinja2 as an option.

Ansible, Inc. offers paid support for Ansible and an optional web-based addon called `Ansible Tower <http://ansible.com/tower>`_.

|

Chef
----

Chef has basically two modes of operation: The most widely used one involves a server component and the :command:`chef-client` agent. The second option is :command:`chef-solo`, which will apply configuration from a local repository to the node the repository is located on. BundleWrap supports neither of these modes and always applies configuration over SSH.

Overall, Chef is harder to get into, but will scale to thousands of nodes.

The community around Chef is quite large and probably the largest of all config management systems. This means lots of community-maintained cookbooks to choose from. BundleWrap does have a :doc:`plugin system <plugins>` to provide almost anything in a repository, but there aren't many plugins to choose from yet.

Chef is written in Ruby and uses the popular `ERB <http://www.kuwata-lab.com/erubis/>`_ template language. BundleWrap is heavily invested in Python and offers support for Mako and Jinja2 templates.

OpsCode offers paid support for Chef and SaaS hosting for the server component. `AWS OpsWorks <http://aws.amazon.com/opsworks/>`_ also integrates Chef cookbooks.

|
