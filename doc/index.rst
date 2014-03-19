Blockwart documentation
=======================

.. todolist::

By allowing for easy and low-overhead config management, Blockwart fills the gap between complex deployments using Chef or Puppet and old school system administration over SSH.

|

How does it work?
-----------------

While practically all other config management systems rely on a client-server architecture, Blockwart works off a repository cloned to your local machine. It then automates the process of SSHing into your servers and making sure everything is configured the way it's supposed to be. You won't have to install anything on managed servers.

Check out the :doc:`quickstart tutorial <quickstart>` to get started.

|

Is Blockwart the right tool for you?
------------------------------------

We think you will enjoy Blockwart a lot if you:

* know some Python
* like to write your configuration from scratch and control every bit of it
* have lots of unique nodes
* are trying to get a lot of existing systems under management
* are NOT trying to handle a massive amount of nodes (let's say more than 300)
* like to start small
* don't want yet more stuff to run on your nodes
* prefer a simple tool to a fancy one
* want as much as possible in git/hg/bzr
* have strongly segmented internal networks

You might be better served with a different config management system if you:

* hate Python and/or JSON
* like to use community-maintained configuration templates
* need unattended bootstrapping of nodes
* don't want to use SSH with key-based authentication and passwordless sudo to manage your nodes
* need to manage non-Linux systems


.. raw:: html

   <div style="display: none;">

.. toctree::
   :maxdepth: 1

   quickstart
   installation
   requirements
   repository
   cli
   api
   dev_contrib
   faq
   about

.. raw:: html

   </div>
