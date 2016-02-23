# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from bundlewrap.utils.testing import make_repo, run


def test_file_preview(tmpdir):
    make_repo(
        tmpdir,
        nodes={
            "node1": {
                'bundles': ["bundle1"],
            },
        },
        bundles={
            "bundle1": {
                'files': {
                    "/test": {
                        'content': "föö",
                        'encoding': 'latin-1',
                    },
                },
            },
        },
    )

    stdout, stderr, rcode = run("bw items -f /test node1", path=str(tmpdir))
    assert stdout == "föö".encode('utf-8')  # our output is always utf-8
