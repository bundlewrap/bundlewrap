# Migrating from BundleWrap 2.x to 3.x

As per [semver](http://semver.org), BundleWrap 3.0 breaks compatibility with repositories created for BundleWrap 2.x. This document provides a guide on how to upgrade your repositories to BundleWrap 3.x. Please read the entire document before proceeding.

<br>

## metadata.py

BundleWrap 2.x simply used all functions in `metadata.py` whose names don't start with an underscore as metadata processors. This led to awkward imports like `from foo import bar as _bar`. BundleWrap 3.x provides a decorator for explicitly designating funtions as metadata processors:

	@metadata_processor
	def myproc(metadata):
	    return metadata, True

You will have to add `@metadata_processor` to each metadata processor function. There is no need to import it; it is provided automatically, just like `node` and `repo`.
