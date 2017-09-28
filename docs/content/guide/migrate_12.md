# Migrating from BundleWrap 1.x to 2.x

As per [semver](http://semver.org), BundleWrap 2.0 breaks compatibility with repositories created for BundleWrap 1.x. This document provides a guide on how to upgrade your repositories to BundleWrap 2.x. Please read the entire document before proceeding. To aid with the transition, BundleWrap 1.6.0 has been released along with 2.0.0. It contains no new features over 1.5.x, but has builtin helpers to aid your migration to 2.0.

<br>

## items.py

In every bundle, rename `bundle.py` to `items.py`. BundleWrap 1.6.0 can do this for you by running `bw migrate`.

<br>

## Default file content type

The default `content_type` for [file items](../items/file.md) has changed from "mako" to "text". This means that you need to check all file items that do not define an explicit content type of "mako". Some of them might be fine because you didn't really need templating, while others may need to have their `content_type` set to "mako" explicitly.

BundleWrap 1.6.0 will print warnings for every file item affected when running `bw test`.

<br>

## Metadata merging

The merging behavior for node and group metadata has changed. Instead of a simple `dict.update()`, metadata dicts are now merged recursively. See [the docs](../repo/groups.py.md#metadata) for details.

<br>

## Metadata processors and item generators

These two advanced features have been replaced by a single new mechanism: [metadata.py](../repo/metadata.py.md) You will need to rethink and rewrite them.

BundleWrap 1.6.0 will print warnings for every group that uses metadata processors and any item generators when running `bw test`.

<br>

## Custom item types

The API for defining your own items has changed. Generally, you should be able to upgrade your items with relatively little effort. Refer to [the docs](dev_item.md) for details.

<br>

## Deterministic templates

While not a strict requirement, it is highly recommended to ensure your entire configuration can be created deterministically (i.e. remains exactly the same no matter how often you generate it). Otherwise, you won't be able to take advantage of the new functionality provided by `bw hash`.

A common pitfall here is iteration over dictionaries in templates:

	% for key, value in my_dict.items():
	${value}
	% endfor

Standard dictionaries in Python have no defined order. This may result in lines occasionally changing their position. To solve this, you can simply use `sorted()`:

	% for key, value in sorted(my_dict.items()):
	${value}
	% endfor

<br>

## Hook arguments

Some [hooks](../repo/hooks.md) had their arguments adjusted slightly.
