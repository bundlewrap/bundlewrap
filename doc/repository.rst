####################
Repository reference
####################

A Blockwart repository contains everything you need to contruct the configuration for your systems.

This page describes the various subdirectories and files than can exist inside a repo.

.. raw:: html

   <style type="text/css">.wy-table-responsive table td { vertical-align: top !important; white-space: normal !important; }</style>

+-----------------+-----------------+------------------------------------------------------------------------------------------------------------------------------------------+
| Name            | Documentation   | Purpose                                                                                                                                  |
+=================+=================+==========================================================================================================================================+
| ``nodes.py``    | :ref:`nodespy`  | This file tells Blockwart what nodes (servers, VMs, ...) there are in your environment and lets you configure options such as hostnames. |
+-----------------+-----------------+------------------------------------------------------------------------------------------------------------------------------------------+
| ``groups.py``   | :ref:`groupspy` | This file allows you to organize your nodes into groups.                                                                                 |
+-----------------+-----------------+------------------------------------------------------------------------------------------------------------------------------------------+
| ``bundles/``    | :ref:`bundles`  | This required subdirectory contains the bulk of your configuration, organized into bundles of related items.                             |
+-----------------+-----------------+------------------------------------------------------------------------------------------------------------------------------------------+
| ``items/``      | :ref:`dev_item` | This optional subdirectory contains the code for your custom item types.                                                                 |
+-----------------+-----------------+------------------------------------------------------------------------------------------------------------------------------------------+
| ``libs/``       | :ref:`libs`     | This optional subdirectory contains reusable custom code for your bundles.                                                               |
+-----------------+-----------------+------------------------------------------------------------------------------------------------------------------------------------------+




.. raw:: html

   <div style="display: none;">

.. toctree::
   :maxdepth: 1

   nodes.py
   groups.py
   bundles
   hooks
   dev_item
   libs

.. raw:: html

   </div>
