# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from bundlewrap.utils.testing import host_os, make_repo, run


def test_action_success(tmpdir):
    make_repo(
        tmpdir,
        bundles={
            "test": {
                'actions': {
                    "success": {
                        'command': "true",
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
    run("bw apply localhost", path=str(tmpdir))


def test_action_fail(tmpdir):
    make_repo(
        tmpdir,
        bundles={
            "test": {
                'actions': {
                    "failure": {
                        'command': "false",
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
    run("bw apply localhost", path=str(tmpdir))


def test_action_pipe(tmpdir):
    make_repo(
        tmpdir,
        bundles={
            "test": {
                'actions': {
                    "pipe": {
                        'command': "cat",
                        'data_stdin': "hello 🐧\n",
                        'expected_stdout': "hello 🐧\n",
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
    run("bw apply localhost", path=str(tmpdir))
