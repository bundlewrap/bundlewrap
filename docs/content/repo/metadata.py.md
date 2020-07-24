# metadata.py

Alongside `items.py` you may create another file called `metadata.py`. It can be used to define defaults and do advanced processing of the metadata you configured for your nodes and groups. Specifically, it allows each bundle to modify metadata before `items.py` is evaluated.


## Defaults

Let's look at defaults first:

	defaults = {
	    "foo": 5,
	}

This will simply ensure that the `"foo"` key in metadata will always be set, but the default value of 5 can be overridden by node or group metadata or metadata reactors.


## Reactors

So let's look at reactors next. Metadata reactors are functions that take the metadata generated for this node so far as their single argument. You must then return a new dictionary with any metadata you wish to have added:

	@metadata_reactor
	def bar(metadata):
	    return {
	        "bar": metadata.get("foo"),
	    }

While this looks simple enough, there are some important caveats. First and foremost: Metadata reactors must assume to be called many times. This is to give you an opportunity to react to metadata provided by other reactors. All reactors will be run again and again until none of them return any changed metadata. Anything you return from a reactor will overwrite defaults, while metadata from `groups.py` and `nodes.py` will still overwrite metadata from reactors. Collection types like sets and dicts will be merged.

The parameter `metadata` is not a dictionary but an instance of `Metastack`. You cannot modify the contents of this object. It provides `.get("some/path", "default")` to query a key path (equivalent to `metadata["some"]["path"]` in a dict) and accepts an optional default value. It will raise a `KeyError` when called for a non-existant path without a default.

While node and group metadata and metadata defaults will always be available to reactors, you should not rely on that for the simple reason that you may one day move some metadata from those static sources into another reactor, which may be run later. Thus you may need to wait for some iterations before that data shows up in `metadata`. Note that BundleWrap will catch any `KeyError`s raised in metadata reactors and only report them if they don't go away after all other relevant reactors are done.

You can also access other nodes' metadata:

	@metadata_reactor
	def baz(metadata):
	    frob = set()
	    for n in repo.nodes:
	        frob.add(n.metadata.get('sizzle'))
	    return {'frob': frob}


### DoNotRunAgain

On the other hand, if your reactor only needs to provide new metadata in *some* cases, you can tell BundleWrap to not run it again to save some performance:

	@metadata_reactor
	def foo(metadata):
	    if node.has_bundle("bar"):
	        return {"bar": metadata.get("foo") + 1}
	    else:
	        raise DoNotRunAgain


<div class="alert alert-info">For your convenience, you can access <code>repo</code>, <code>node</code>, <code>metadata_reactors</code>, and <code>DoNotRunAgain</code> in <code>metadata.py</code> without importing them.</div>


## Priority

For atomic ("primitive") data types like `int` or `bool`:

1.  Nodes
2.  Groups
3.  Reactors
4.  Defaults

Node metadata wins over group metadata, groups win over reactors, reactors win over defaults.

This also applies to type conflicts: For example, specifying a boolean flag in node metadata will win over a list returned by a metadata reactor. (You should probably avoid situations like this entirely.)

Set-like data types will be merged recursively.

<div class="alert alert-info">Also see the <a href="../nodes.py#metadata">documentation for node.metadata</a> and <a href="../groups.py#metadata">group.metadata</a> for more information.</div>
