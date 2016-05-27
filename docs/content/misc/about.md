<style>.bs-sidebar { display: none; }</style>

# About

Development on BundleWrap started in July 2012, borrowing some ideas from [Bcfg2](http://bcfg2.org/). Some key features that are meant to set BundleWrap apart from other config management systems are:

* decentralized architecture
* pythonic and easily extendable
* easy to get started with
* true item-level parallelism (in addition to working on multiple nodes simultaneously, BundleWrap will continue to fix config files while installing a package on the same node)
* very customizable item dependencies
* collaboration features like [node locking](../guide/locks.md) (to prevent simultaneous applies to the same node) and hooks for chat notifications
* built-in testing facility (`bw test`)
* can be used as a library

BundleWrap is a "pure" free software project licensed under the terms of the [GPLv3](http://www.gnu.org/licenses/gpl.html>), with no *Enterprise Edition* or commercial support.
