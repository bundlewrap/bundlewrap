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
                'items': {
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
        },
    )

    stdout, stderr, rcode = run("bw stats", path=str(tmpdir))
    assert stdout == """╭───────┬───────────────────╮
│ count │ type              │
├───────┼───────────────────┤
│     1 │ nodes             │
│     0 │ groups            │
│     1 │ bundles           │
│     0 │ metadata defaults │
│     0 │ metadata reactors │
│     2 │ items             │
├───────┼───────────────────┤
│     2 │ file              │
╰───────┴───────────────────╯
""".encode('utf-8')
