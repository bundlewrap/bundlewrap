<style>.bs-sidebar { display: none; }</style>

Repository layout
=================

A BundleWrap repository contains everything you need to contruct the configuration for your systems.

This page describes the various subdirectories and files than can exist inside a repo.

<br>

<table>
<tr>
<td><a href="/repo/nodes.py">nodes.py</a></td>
<td>This file tells BundleWrap what nodes (servers, VMs, ...) there are in your environment and lets you configure options such as hostnames.</td>
</tr>
<tr>
<td><a href="/repo/groups.py">groups.py</a></td>
<td>This file allows you to organize your nodes into groups.</td>
</tr>
<tr>
<td>bundles/</td>
<td>This required subdirectory contains the bulk of your configuration, organized into bundles of related items. Each bundle is a subdirectory of bundles/ with an <a href="/repo/items.py">items.py</a> or <a href="/repo/metadata.py">metadata.py</a> in it (or both).</td>
</tr>
<tr>
<td>data/</td>
<td>This optional subdirectory contains data files that are not generic enough to be included in bundles (which are meant to be shareable).</td>
</tr>
<tr>
<td><a href="/repo/hooks">hooks/</a></td>
<td>This optional subdirectory contains hooks you can use to act on certain events when using BundleWrap.</td>
</tr>
<tr>
<td><a href="/guide/dev_item">items/</a></td>
<td>This optional subdirectory contains the code for your custom item types.</td>
</tr>
<tr>
<td><a href="/repo/libs">libs/</a></td>
<td>This optional subdirectory contains reusable custom code for your bundles.</td>
</tr>
</table>
