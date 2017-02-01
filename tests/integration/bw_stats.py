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
    assert stdout == """i ╭───────┬─────────────────────╮
i │ Count │ Type                │
i ├───────┼─────────────────────┤
i │     1 │ nodes               │
i │     0 │ groups              │
i │     1 │ bundles             │
i │     0 │ metadata processors │
i │     2 │ items               │
i ├───────┼─────────────────────┤
i │     2 │ file                │
i ╰───────┴─────────────────────╯
""".encode('utf-8')
