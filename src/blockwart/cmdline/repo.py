# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from ..repo import Repository


def bw_repo_bundle_create(repo, args):
    repo.create_bundle(args.bundle)


def bw_repo_create(path, args):
    Repository.create(path)
