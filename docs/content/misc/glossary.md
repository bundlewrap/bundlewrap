# Glossary

## action

Actions are a special kind of item used for running shell commands during each `bw apply`. They allow you to do things that aren't persistent in nature.

<br>

## apply

An "apply" is what we call the process of what's otherwise known as "converging" the state described by your repository and the actual status quo on the node.

<br>

## bundle

A collection of items. Most of the time, you will create one bundle per application. For example, an Apache bundle will include the httpd service, the virtual host definitions and the apache2 package.

<br>

## group

Used for organizing your nodes.

<br>

## hook

[Hooks](../repo/hooks.md) can be used to run your own code automatically during various stages of BundleWrap operations.

<br>

## item

A single piece of configuration on a node, e.g. a file or an installed package.

You might be interested in [this overview of item types](../repo/items.py.md#item_types).

<br>

## lib

[Libs](../repo/libs.md) are a way to store Python modules in your repository and make them accessible to your bundles and templates.

<br>

## node

A managed system, no matter if physical or virtual.

<br>

## repo

A repository is a directory with [some stuff](../repo/layout.md) in it that tells BundleWrap everything it needs to know about your infrastructure.
