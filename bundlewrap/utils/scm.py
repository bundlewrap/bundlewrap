# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from subprocess import CalledProcessError, check_output, STDOUT


def get_bzr_rev():
    try:
        return check_output(
            "bzr revno",
            shell=True,
            stderr=STDOUT,
        ).strip()
    except CalledProcessError:
        return None


def get_git_rev():
    try:
        return check_output(
            "git rev-parse HEAD",
            shell=True,
            stderr=STDOUT,
        ).strip()
    except CalledProcessError:
        return None


def get_hg_rev():
    try:
        return check_output(
            "hg --debug id -i",
            shell=True,
            stderr=STDOUT,
        ).strip().rstrip("+")
    except CalledProcessError:
        return None


def get_rev():
    for scm_rev in (get_git_rev, get_hg_rev, get_bzr_rev):
        rev = scm_rev()
        if rev is not None:
            return rev
    return None
