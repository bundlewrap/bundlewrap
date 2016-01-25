# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from os import rename
from os.path import join


def bw_migrate(repo, args):
    for bundle in repo.bundle_names:
        try:
            old = join(repo.path, "bundles", bundle, "bundle.py")
            new = join(repo.path, "bundles", bundle, "items.py")
            yield "renaming {} -> {}".format(old, new)
            rename(old, new)
        except Exception as e:
            yield str(e)
