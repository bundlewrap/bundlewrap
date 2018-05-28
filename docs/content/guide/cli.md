# Command Line Interface

The `bw` utility is BundleWrap's command line interface.

<div class="alert alert-info">This page is not meant as a complete reference. It provides a starting point to explore the various subcommands. If you're looking for details, <code>--help</code> is your friend.</div>

## bw apply

<pre><code class="nohighlight">bw apply -i mynode</code></pre>

The most important and most used part of BundleWrap, `bw apply` will apply your configuration to a set of [nodes](../repo/nodes.py.md). By default, it operates in a non-interactive mode. When you're trying something new or are otherwise unsure of some changes, use the `-i` switch to have BundleWrap interactively ask before each change is made.

<br>

## bw run

<pre><code class="nohighlight">$ bw run mygroup "uname -a"</code></pre>

Unsurprisingly, the `run` subcommand is used to run commands on nodes.

As with most commands that accept node names, you can also give a `group` name or any combination of node and group names, separated by commas (without spaces, e.g. `node1,group2,node3`). A third option is to use a bundle selector like `bundle:my_bundle`. It will select all nodes with the named `bundle`. You can freely mix and match node names, group names, and bundle selectors.

Negation is also possible for bundles and groups. `!bundle:foo` will add all nodes without the foo bundle, while `!group:foo` will add all nodes that aren't in the foo group.

<br>

## bw debug

	$ bw debug
	bundlewrap X.Y.Z interactive repository inspector
	> You can access the current repository as 'repo'.
	>>> len(repo.nodes)
	121

This command will drop you into a Python shell with direct access to BundleWrap's [API](api.md). Once you're familiar with it, it can be a very powerful tool.

<br>

## bw plot

<div class="alert alert-info">You'll need <a href="http://www.graphviz.org">Graphviz</a> installed on your machine for this to be useful.</div>

<pre><code class="nohighlight">$ bw plot node mynode | dot -Tsvg -omynode.svg</code></pre>

You won't be using this every day, but it's pretty cool. The above command will create an SVG file (you can open these in your browser) that shows the item dependency graph for the given node. You will see bundles as dashed rectangles, static dependencies (defined in BundleWrap itself) in green, auto-generated dependencies (calculated dynamically each time you run `bw apply`) in blue and dependencies you defined yourself in red.

It offers an interesting view into the internal complexities BundleWrap has to deal with when figuring out the order in which your items can be applied to your node.

<br>

## bw test

<pre><code class="nohighlight">$ bw test
✓ node1  samba  pkg_apt:samba
✘ node1  samba  file:/etc/samba/smb.conf

[...]

+----- traceback from worker ------
|
|  Traceback (most recent call last):
|    File "bundlewrap/concurrency.py", line 78, in _worker_process
|      return_value = target(*msg['args'], **msg['kwargs'])
|    File "&lt;string&gt;", line 378, in test
|  BundleError: file:/etc/samba/smb.conf from bundle 'samba' refers to missing file '/path/to/bundlewrap/repo/bundles/samba/files/smb.conf'
|
+----------------------------------
</code></pre>

This command is meant to be run automatically like a test suite after every commit. It will try to catch any errors in your bundles and file templates by initializing every item for every node (but without touching the network).
