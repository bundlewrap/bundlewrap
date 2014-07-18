About
=====

.. toctree::

Development on Blockwart started in July 2012, borrowing some ideas from `Bcfg2 <http://bcfg2.org/>`_. Some key features that are meant to set Blockwart apart from other config management systems are:

* decentralized architecture
* pythonic and easily extendable
* easy to get started with
* true item-level parallelism (in addition to working on multiple nodes simultaneously, Blockwart will continue to fix config files while installing a package on the same node)
* very customizable item dependencies
* collaboration features like node locking (to prevent simultaneous applies to the same node) and hooks for chat notifications
* built-in testing facility (:command:`bw test`)
* can be used as a library

Blockwart is a "pure" free software project licensed under the terms of the `GPLv3 <http://www.gnu.org/licenses/gpl.html>`_, with no *Enterprise Edition* or commercial support.

|

.. _about_name:

The name "Blockwart" is actually a German word invented by the Nazi party. It was the lowest party rank bestowed on individuals who were responsible for political supervision of a city block or neighborhood. A literal translation would be *block warden*. The term is still used in modern-day German as a derogatory title for people who are overly concerned with the strict adherence to (often insignificant) rules and social conventions. A typical modern *Blockwart* will not hesitate to bring it to your (and everyone else's) attention that your lawn could use some mowing and how long has it been since your vehicle has seen a car wash? Three weeks now?

The relation to config management is that you define some arbitrary rules and Blockwart makes sure all your systems abide by those rules. There is an :ref:`entry in the FAQ <name>` about the somewhat controversial nature of the name.
