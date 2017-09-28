Quickstart
==========

This is the 10 minute intro into BundleWrap. Fasten your seatbelt.


Installation
------------

First, open a terminal and install BundleWrap:

<pre><code class="nohighlight">pip install bundlewrap</code></pre>


Create a repository
-------------------

Now you'll need to create your [repository](../repo/layout.md):

<pre><code class="nohighlight">mkdir my_bundlewrap_repo
cd my_bundlewrap_repo
bw repo create
</code></pre>

You will note that some files have been created. Let's check them out:

<pre><code class="nohighlight">cat nodes.py
cat groups.py
</code></pre>

The contents should be fairly self-explanatory, but you can always check the [docs](../repo/layout.md) on these files if you want to go deeper.

<div class="alert alert-info">It is highly recommended to use git or a similar tool to keep track of your repository. You may want to start doing that right away.</div>

At this point you will want to edit `nodes.py` and maybe change "localhost" to the hostname of a system you have passwordless (including sudo) SSH access to.

<div class="alert alert-info">BundleWrap will honor your <code>~/.ssh/config</code>, so if <code>ssh mynode.example.com sudo id</code> works without any password prompts in your terminal, you're good to go.</div>


Run a command
-------------

The first thing you can do is run a command on your army of one node:

<pre><code class="nohighlight">bw -a run node-1 "uptime"</code></pre>

<div class="alert alert-info">The <code>-a</code> switch tells bw to automatically trust unknown SSH host keys (when you're connecting to a new node). By default, only known host keys will be accepted.</div>

You should see something like this:

<pre><code class="nohighlight">› node-1   20:16:26 up 34 days,  4:10,  0 users,  load average: 0.00, 0.01, 0.05
✓ node-1  completed after 0.366s</code></pre>

Instead of a node name ("node-1" in this case) you can also use a group name (such as "all") from your `groups.py`.


Create a bundle
---------------

BundleWrap stores node configuration in bundles. A bundle is a collection of *items* such as files, system packages or users. To create your first bundle, type:

<pre><code class="nohighlight">bw repo bundle create mybundle</code></pre>

Now that you have created your bundle, it's important to tell BundleWrap which nodes will have this bundle. You can assign bundles to nodes using either <code>groups.py</code> or <code>nodes.py</code>, here we'll use the latter:

	nodes = {
	    'node-1': {
	        'bundles': (
	            "mybundle",
	        ),
	        'hostname': "mynode-1.local",
	    },
	}


Create a file template
----------------------

To manage a file, you need two things:

1. a file item in your bundle
2. a template for the file contents

Add this to your `bundles/mybundle/items.py`:

	files = {
	    '/etc/motd': {
	        'content_type': 'mako',  # use the Mako template engine for this file
	        'source': "mymotd",  # filename of the template
	    },
	}

Then write the file template:

<pre><code class="nohighlight">vim bundles/mybundle/files/mymotd</code></pre>

You can use this for example content:

<pre><code class="nohighlight">Welcome to ${node.name}!</code></pre>

Note that the `source` attribute in `items.py` contains a path relative to the `files` directory of your bundle.


Apply configuration
-------------------

Now all that's left is to run `bw apply`:

<pre><code class="nohighlight">bw apply -i node-1</code></pre>

BundleWrap will ask to replace your previous MOTD:

<pre><code class="nohighlight">i node-1  started at 2016-02-13 21:25:45
? node-1
? node-1  ╭─ file:/etc/motd
? node-1  │
? node-1  │  content
? node-1  │  --- &lt;node&gt;
? node-1  │  +++ &lt;bundlewrap&gt;
? node-1  │  @@ -1 +1 @@
? node-1  │  -your old motd
? node-1  │  +Welcome to node-1!
? node-1  │
? node-1  ╰─ Fix file:/etc/motd? [Y/n]
</code></pre>

That completes the quickstart tutorial!


Further reading
---------------

Here are some suggestions on what to do next:

* set up [SSH multiplexing](https://en.wikibooks.org/wiki/OpenSSH/Cookbook/Multiplexing) for significantly better performance
* take a moment to think about what groups and bundles you will create
* read up on how a [BundleWrap repository](../repo/layout.md) is laid out
* ...especially what [types of items](../repo/items.py.md#item-types) you can add to your bundles
* familiarize yourself with [the Mako template language](http://www.makotemplates.org/)
* explore the [command line interface](cli.md)
* follow [@bundlewrap](https://twitter.com/bundlewrap) on Twitter

Have fun! If you have any questions, feel free to drop by [on IRC](irc://chat.freenode.net/bundlewrap).
