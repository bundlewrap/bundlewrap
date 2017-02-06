# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from bundlewrap.utils.testing import make_repo, run


def test_nondeterministic(tmpdir):
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
                        'content': "foo",
                    },
                    "/test2": {
                        'content': "foo",
                    },
                },
            },
        },
    )

    stdout, stderr, rcode = run("bw stats", path=str(tmpdir))
    assert stdout == """╭───────┬─────────────────────╮
│ count │ type                │
├───────┼─────────────────────┤
│     1 │ nodes               │
│     0 │ groups              │
│     1 │ bundles             │
│     0 │ metadata processors │
│     2 │ items               │
├───────┼─────────────────────┤
│     2 │ file                │
╰───────┴─────────────────────╯
""".encode('utf-8')
