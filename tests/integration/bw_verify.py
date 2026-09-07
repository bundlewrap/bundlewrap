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


def test_fault_content_unavailable_skipped(tmpdir):
    make_repo(
        tmpdir,
        bundles={
            "test": {
                'items': {},
            },
        },
        nodes={
            "localhost": {
                'bundles': ["test"],
                'os': host_os(),
            },
        },
    )
    with open(join(str(tmpdir), "bundles", "test", "items.py"), 'w') as f:
        f.write("""
files = {
    "/tmp/bw_test_faultunavailable": {
        'content': repo.vault.password_for("fault", key="missing"),
    },
}
""")
    stdout, stderr, rcode = run("bw verify localhost", path=str(tmpdir))
    assert rcode == 0
    assert b"file:/tmp/bw_test_faultunavailable  (Fault unavailable)" in stdout
    assert b"unable to get status" not in stderr
