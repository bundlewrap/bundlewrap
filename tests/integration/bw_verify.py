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


def test_fault_unavailable_in_template(tmpdir):
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
    "/tmp/bw_test_verify_fault": {
        'content': "${repo.vault.password_for('fault', key='missing')}",
        'content_type': 'mako',
    },
}
""")
    stdout, stderr, rcode = run("bw verify localhost", path=str(tmpdir))
    assert rcode == 0
    assert b"file:/tmp/bw_test_verify_fault  (Fault unavailable)" in stdout
    assert b"Traceback" not in stderr
    assert b"unable to get status" not in stderr


def test_fault_unavailable_error_on_missing_fault(tmpdir):
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
    "/tmp/bw_test_verify_fault_error": {
        'content': "${repo.vault.password_for('fault', key='missing')}",
        'content_type': 'mako',
        'error_on_missing_fault': True,
    },
}
""")
    stdout, stderr, rcode = run("bw verify localhost", path=str(tmpdir))
    assert b"(Fault unavailable)" not in stdout
    assert b"unable to get status" in stderr


def test_fault_unavailable_attribute(tmpdir):
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
    "/tmp/bw_test_verify_fault_attr": {
        'content': repo.vault.password_for('fault', key='missing'),
    },
}
""")
    stdout, stderr, rcode = run("bw verify localhost", path=str(tmpdir))
    assert rcode == 0
    assert b"file:/tmp/bw_test_verify_fault_attr  (Fault unavailable)" in stdout
    assert b"Traceback" not in stderr
