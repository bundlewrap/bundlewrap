# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from os import readlink, symlink
from os.path import join

from bundlewrap.cmdline import main
from bundlewrap.utils.testing import host_os, make_repo


def test_create(tmpdir):
    make_repo(
        tmpdir,
        bundles={
            "test": {
                'symlinks': {
                    join(str(tmpdir), "foo"): {
                        'target': "/dev/null",
                    },
                },
            },
        },
        nodes={
            "localhost": {
                'bundles': ["test"],
                'os': host_os(),
            },
        },
    )
    main("apply", "localhost", path=str(tmpdir))
    assert readlink(join(str(tmpdir), "foo")) == "/dev/null"


def test_fix(tmpdir):
    symlink(join(str(tmpdir), "bar"), join(str(tmpdir), "foo"))
    make_repo(
        tmpdir,
        bundles={
            "test": {
                'symlinks': {
                    join(str(tmpdir), "foo"): {
                        'target': "/dev/null",
                    },
                },
            },
        },
        nodes={
            "localhost": {
                'bundles': ["test"],
                'os': host_os(),
            },
        },
    )
    main("apply", "localhost", path=str(tmpdir))
    assert readlink(join(str(tmpdir), "foo")) == "/dev/null"
