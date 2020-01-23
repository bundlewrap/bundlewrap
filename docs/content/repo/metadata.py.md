# metadata.py

Alongside `items.py` you may create another file called `metadata.py`. It can be used to do advanced processing of the metadata you configured for your nodes and groups. Specifically, it allows each bundle to modify metadata before `items.py` is evaluated.

This is accomplished through metadata processors. There are two kinds of metadata processors: defaults and reactors.


## Defaults

Let's look at defaults first:

	@metadata_defaults
	def foo():
	    return {
	        "foo": 5,
	    }

This will simply ensure that the `"foo"` key in metadata will always be set, but the default value of 5 can be overridden by node or group metadata or metadata reactors.


## Reactors

So let's look at reactors next. Metadata reactors are functions that take the metadata generated so far as their single argument. You must then return a new dictionary with any metadata you wish to have added:

	@metadata_reactor
	def bar(metadata):
	    return {
	        "bar": metadata.get("foo"),
	    }

While this looks simple enough, there are some important caveats. First and foremost: Metadata reactors must assume to be called many times. This is to give you an opportunity to react to metadata provided by other reactors. All reactors will be run again and again until none of them return any changed metadata. Unlike defaults, anything you return from a reactor will overwrite existing metadata.

The parameter `metadata` is not a dictionary but an instance of `Metastack`. It knows two methods, `.get("some/path", "default")` and `.has("some/path")`, which provide `dict`-like access. You cannot modify the contents of this object.

Do not assume `metadata` contains anything. While node and group metadata and the results of metadata defaults will always be available to reactors, you should not rely on that for the simple reason that you may one day move some metadata from those static sources into another reactor, which may be run later. Thus you may need to wait for some iterations before that data shows up in `metadata`.

To avoid deadlocks when accessing *other* nodes' metadata from within a metadata reactor, use `other_node.partial_metadata` instead of `other_node.metadata`. For the same reason, always use the `metadata` parameter to access the current node's metadata, never `node.metadata`.

<div class="alert alert-danger">Be careful when returning <a href="../../guide/api#bundlewraputilsfault">Fault</a> objects from reactors. <strong>All</strong> Fault objects (including those returned from <code>repo.vault.*</code>) will be considered <strong>equal</strong> to one another when BundleWrap inspects the returned metadata to check if anything changed compared to the <code>metadata</code> dict passed into the reactor.</div>


### EXPECT_RESULTS

As a debugging aid, you may return `EXPECT_RESULT` instead of a dict to raise an exception if the metadata you're waiting for never shows up:

	@metadata_reactor
	def foo(metadata):
	    if not metadata.has('something_foo_needs'):
	        return EXPECT_RESULT
	    else:
	        return {'something_new': metadata.get('something_foo_needs', 0) + 1}


	@metadata_reactor
	def bar(metadata):
	    if some_condition:
	        return {'something_foo_needs': 1}
	    else:
	        return {}

You could just return an empty dict instead of `EXPECT_RESULT`, but then you would not be alerted if `"something_foo_needs"` never shows up.


### DO_NOT_RUN_ME_AGAIN

On the other hand, if your reactor only needs to provide new metadata in *some* cases, you can tell BundleWrap to not run it again to save some performance:

	@metadata_reactor
	def foo(metadata):
	    if node.has_bundle("bar"):
	        return {"bar": 1}
	    else:
	        return DO_NOT_RUN_ME_AGAIN


<div class="alert alert-info">For your convenience, you can access <code>repo</code>, <code>node</code>, <code>metadata_defaults</code>, <code>metadata_reactors</code>, <code>EXPECT_RESULT</code> and <code>DO_NOT_RUN_ME_AGAIN</code> in <code>metadata.py</code> without importing them.</div>
