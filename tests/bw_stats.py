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
    assert stdout == b"""1 nodes
0 groups
2 items
  2 file
"""
