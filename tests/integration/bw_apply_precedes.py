# -*- coding: utf-8 -*-
from __future__ import unicode_literals
from os.path import join

from bundlewrap.utils.testing import host_os, make_repo, run


def test_precedes(tmpdir):
    make_repo(
        tmpdir,
        bundles={
            "test": {
                'files': {
                    join(str(tmpdir), "file"): {
                        'content': "1\n",
                        'triggered': True,
                        'precedes': ["tag:tag1"],
                    },
                },
                'actions': {
                    "action2": {
                        'command': "echo 2 >> {}".format(join(str(tmpdir), "file")),
                        'tags': ["tag1"],
                    },
                    "action3": {
                        'command': "echo 3 >> {}".format(join(str(tmpdir), "file")),
                        'tags': ["tag1"],
                        'needs': ["action:action2"],
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
    with open(join(str(tmpdir), "file")) as f:
        content = f.read()
    assert content == "1\n2\n3\n"
