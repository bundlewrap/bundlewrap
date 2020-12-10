# groups.py

This file lets you specify or dynamically build groups of [nodes](nodes.py.md) in your environment.

As with `nodes.py`, you define your groups as a dictionary:

	groups = {
	    'all': {
	        'member_patterns': (
	            r".*",
	        ),
	    },
	    'group1': {
	        'members': (
	            'node1',
	        ),
	    },
	}

All group attributes are optional.

<br>

# Group attribute reference

This section is a reference for all possible attributes you can define for a group:

	groups = {
	    'group1': {
	        # THIS PART IS EXPLAINED HERE
	        'bundles': ["bundle1", "bundle2"],
	        'members': ["node1"],
	        'member_patterns': [r"^cluster1\."],
	        'metadata': {'foo': "bar"},
	        'os': 'linux',
	        'subgroups': ["group2", "group3"],
	        'subgroup_patterns': [r"^group.*pattern$"],
	    },
	}

Note that many attributes from [nodes.py](nodes.py.md) (e.g. `bundles`) may also be set at group level, but aren't explicitly documented here again.

<br>

## member_patterns

A list of regular expressions. Node names matching these expressions will be added to the group members.

Matches are determined using [the search() method](http://docs.python.org/2/library/re.html#re.RegexObject.search).

<br>

## members

A tuple or list of node names that belong to this group.

<br>

## metadata

A dictionary that will be accessible from each node's `node.metadata`. For each node, BundleWrap will merge the metadata of all of the node's groups first, then merge in the metadata from the node itself.

Metadata is merged recursively by default, meaning nested dicts will overlay each other. Lists will be appended to each other, but not recursed into. In come cases, you want to overwrite instead of merge a piece of metadata. This is accomplished through the use of `bundlewrap.metadata.atomic()` and best illustrated as an example:

	from bundlewrap.metadata import atomic

	groups = {
	    'all': {
	        'metadata': {
	            'interfaces': {
	                'eth0': {},
	            },
	            'nameservers': ["8.8.8.8", "8.8.4.4"],
	            'ntp_servers': ["pool.ntp.org"],
	        },
	    },
	    'internal': {
	        'metadata':
	            'interfaces': {
	                'eth1': {},
	            },
	            'nameservers': atomic(["10.0.0.1", "10.0.0.2"]),
	            'ntp_servers': ["10.0.0.1", "10.0.0.2"],
	        },
	    },
	}

A node in both groups will end up with `eth0` *and* `eth1`.

The nameservers however are overwritten, so that nodes that are in both the "all" *and* the "internal" group will only have the `10.0.0.x` ones while nodes just in the "all" group will have the `8.8.x.x` nameservers.

The NTP servers are appended: a node in both groups will have all three of them.

<div class="alert alert-warning">BundleWrap will consider group hierarchy when merging metadata. For example, it is possible to define a default nameserver for the "eu" group and then override it for the "eu.frankfurt" subgroup. The catch is that this only works for groups that are connected through a subgroup hierarchy. Independent groups will have their metadata merged in an undefined order. <code>bw test</code> will report conflicting metadata in independent groups as a metadata collision.</div>

<div class="alert alert-info">Also see the <a href="../nodes.py#metadata">documentation for node.metadata</a> and <a href="../metadata.py#Priority">metadata.py</a> for more information.</div>

<br>

## subgroups

A tuple or list of group names whose members should be recursively included in this group.

<br>

## subgroup_patterns

A list of regular expressions. Nodes in with group names matching these expressions will be added to the group members.

Matches are determined using [the search() method](http://docs.python.org/2/library/re.html#re.RegexObject.search).

<br>

## supergroups

The inverse of `subgroups`. Nodes in this group will be added to all supergroups.

<br>
