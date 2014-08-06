.. _libs:

###########
Custom code
###########

.. toctree::
    :hidden:

The :file:`libs/` subdirectory of your repository provides a convenient place to put reusable code used throughout your bundles and hooks.

A Python module called :file:`example.py` placed in this directory will be available as ``repo.libs.example`` wherever you have access to a :py:class:`bundlewrap.repo.Repository` object. In :file:`nodes.py` and :file:`groups.py`, you can do the same thing with just ``libs.example``.

.. warning::
	Only single files, no subdirectories or packages, are supported at the moment.
