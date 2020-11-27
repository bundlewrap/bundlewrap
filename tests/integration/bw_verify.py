from os.path import join

from bundlewrap.utils.testing import host_os, make_repo, run


def test_empty_verify(tmpdir):
    make_repo(
        tmpdir,
        bundles={
            "test": {
                'items': {
                    'files': {
                        join(str(tmpdir), "foo"): {
                            'content_type': 'any',
                        },
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

    with open(join(str(tmpdir), "foo"), 'w') as f:
        f.write("test")

    stdout, stderr, rcode = run("bw verify localhost", path=str(tmpdir))
    assert rcode == 0
