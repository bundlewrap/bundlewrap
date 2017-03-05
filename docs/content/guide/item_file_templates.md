# Writing file templates

BundleWrap can use [Mako](http://www.makotemplates.org) or [Jinja2](http://jinja.pocoo.org) for file templating. This enables you to dynamically contruct your config files. Templates reside in the `files` subdirectory of a bundle and are bound to a file item using the `source` [attribute](../items/file.md#source). This page explains how to get started with Mako.

The most basic example would be:

<pre><code class="nohighlight">Hello, this is ${node.name}!</code></pre>

After template rendering, it would look like this:

<pre><code class="nohighlight">Hello, this is myexamplenodename!</code></pre>

As you can see, `${...}` can be used to insert the value of a context variable into the rendered file. By default, you have access to two variables in every template: `node` and `repo`. They are `bundlewrap.node.Node` and `bundlewrap.repo.Repository` objects, respectively. You can learn more about the attributes and methods of these objects in the [API docs](api.md), but here are a few examples:

<br>

## Examples

inserts the DNS hostname of the current node

	${node.hostname}

<br>

a list of all nodes in your repo

	% for node in repo.nodes:
	${node.name}
	% endfor

<br>

make exceptions for certain nodes

	% if node.name == "node1":
	option = foo
	% elif node.name in ("node2", "node3"):
	option = bar
	% else:
	option = baz
	% endif

<br>

check for group membership

	% if node.in_group("sparkle"):
	enable_sparkles = 1
	% endif

<br>

check for membership in any of several groups

	% if node.in_any_group(("sparkle", "shiny")):
	enable_fancy = 1
	% endif

<br>

check for bundle

	% if node.has_bundle("sparkle"):
	enable_sparkles = 1
	% endif

<br>

check for any of several bundles

	% if node.has_any_bundle(("sparkle", "shiny")):
	enable_fancy = 1
	% endif

<br>

list all nodes in a group

	% for gnode in repo.get_group("mygroup").nodes:
	${gnode.name}
	% endfor

<br>

## Working with node metadata

Quite often you will attach custom metadata to your nodes in `nodes.py`, e.g.:

 	nodes = {
 		"node1": {
 			"metadata": {
 				"interfaces": {
 					"eth0": "10.1.1.47",
 					"eth1": "10.1.2.47",
 				},
 			},
 		},
 	}

You can easily access this information in templates:

	% for interface, ip in sorted(node.metadata["interfaces"].items()):
	interface ${interface}
		ip = ${ip}
	% endfor

This template will render to:

	interface eth0
		ip = 10.1.1.47
	interface eth1
		ip = 10.1.2.47

