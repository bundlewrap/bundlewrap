Blockwart documentation
=======================

.. todolist::

By allowing for easy and low-overhead config management, Blockwart fills the gap between complex deployments using Chef or Puppet and old school system administration over SSH.

|

How does it work?
-----------------

While practically all other config management systems rely on a client-server architecture, Blockwart works off a repository cloned to your local machine. It then automates the process of SSHing into your servers and making sure everything is configured the way it's supposed to be. You won't have to install anything on managed servers.

Check out the :doc:`quickstart tutorial <quickstart>` to get started.

.. raw:: html

   <div style="display: none;">

.. toctree::
   :maxdepth: 1

   quickstart
   installation
   requirements
   repository
   api
   about

.. raw:: html

   </div>
