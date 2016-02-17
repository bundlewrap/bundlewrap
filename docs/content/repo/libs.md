<style>.bs-sidebar { display: none; }</style>

# Custom code

The `libs/` subdirectory of your repository provides a convenient place to put reusable code used throughout your bundles and hooks.

A Python module called `example.py` placed in this directory will be available as `repo.libs.example` wherever you have access to a `bundlewrap.repo.Repository` object. In `nodes.py` and `groups.py`, you can do the same thing with just `libs.example`.

<div class="alert alert-warning">Only single files, no subdirectories or packages, are supported at the moment.</div>
