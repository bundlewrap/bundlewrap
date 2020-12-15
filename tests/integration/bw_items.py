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
                'items': {
                    'files': {
                        "/test": {
                            'content': "föö",
                            'encoding': 'latin-1',
                        },
                    },
                },
            },
        },
    )

    stdout, stderr, rcode = run("bw items -f node1 file:/test", path=str(tmpdir))
    assert stdout == "föö".encode('utf-8')  # our output is always utf-8
    assert rcode == 0


def test_multiple_file_preview(tmpdir):
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
                            'content': "föö",
                        },
                        "/testdir/test2": {
                            'content': "bar",
                        },
                    },
                },
            },
        },
    )

    stdout, stderr, rcode = run("bw items -w itemprev node1", path=str(tmpdir))
    assert rcode == 0
    assert tmpdir.join("itemprev/test").exists()
    assert tmpdir.join("itemprev/testdir/test2").exists()


def test_fault_unavailable(tmpdir):
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
                            'content': "${repo.vault.password_for('test', key='404')}",
                            'content_type': 'mako',
                        },
                    },
                },
            },
        },
    )

    stdout, stderr, rcode = run("bw items -f node1 file:/test", path=str(tmpdir))
    assert rcode == 1


def test_fault_unavailable_multiple(tmpdir):
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
                            'content': "föö",
                        },
                        "/testdir/test3": {
                            'content': "${repo.vault.password_for('test', key='404')}",
                            'content_type': 'mako',
                        },
                    },
                },
            },
        },
    )

    stdout, stderr, rcode = run("bw items -w itemprev node1", path=str(tmpdir))
    assert rcode == 0
    assert tmpdir.join("itemprev/test").exists()
    assert not tmpdir.join("itemprev/testdir/test3").exists()
