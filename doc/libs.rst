.. _libs:

###########
Custom code
###########

.. toctree::
    :hidden:

The ``libs/`` subdirectory of your repository provides a convenient place to put reusable code used throughout your bundles and hooks.

A Python module called ``example.py`` placed in this directory will be available as ``repo.libs.example`` wherever you have access to a :py:class:`blockwart.repo.Repository` object.

.. warning::
	Only single files, no subdirectories or packages, are supported at the moment.
