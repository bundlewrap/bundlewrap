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


def test_tag_inheritance(tmpdir):
    make_repo(
        tmpdir,
        nodes={
            "node1": {
                'bundles': ["bundle1"],
            },
        },
        bundles={
            "bundle1": {
                'attrs': {
                    'tags': {
                        "directly": {
                            'tags': {"inherited"},
                        },
                    },
                },
                'items': {
                    'actions': {
                        "test": {
                            'command': "true",
                            'tags': {"directly"},
                        },
                    },
                },
            },
        },
    )
    stdout, stderr, rcode = run("bw items --attrs node1 action:test", path=str(tmpdir))
    assert rcode == 0
    assert "inherited" in stdout.decode()


def test_tag_inheritance_loop(tmpdir):
    make_repo(
        tmpdir,
        nodes={
            "node1": {
                'bundles': ["bundle1"],
            },
        },
        bundles={
            "bundle1": {
                'attrs': {
                    'tags': {
                        "directly": {
                            'tags': {"inherited"},
                        },
                        "inherited": {
                            'tags': {"looped"},
                        },
                        "looped": {
                            'tags': {"inherited"},
                            'needs': {"action:dep"},
                        },
                    },
                },
                'items': {
                    'actions': {
                        "test": {
                            'command': "true",
                            'tags': {"directly"},
                        },
                        "dep": {
                            'command': "true",
                        },
                    },
                },
            },
        },
    )
    stdout, stderr, rcode = run("bw items --attrs node1 action:test", path=str(tmpdir))
    assert rcode == 0
    assert "inherited" in stdout.decode()
    assert "looped" in stdout.decode()
    assert "action:dep" in stdout.decode()


def test_duplicate_items(tmpdir):
    make_repo(
        tmpdir,
        nodes={
            "node1": {
                'bundles': ["bundle1", "bundle2"],
            },
        },
        bundles={
            "bundle1": {
                'items': {
                    'actions': {
                        "dupl": {
                            'command': "true",
                        },
                    },
                },
            },
            "bundle2": {
                'items': {
                    'actions': {
                        "dupl": {
                            'command': "true",
                        },
                    },
                },
            },
        },
    )
    stdout, stderr, rcode = run("bw items node1", path=str(tmpdir))
    assert rcode == 1
    assert "action:dupl" in stderr.decode()
    assert "bundle1" in stderr.decode()
    assert "bundle2" in stderr.decode()


def test_show_auto_needs(tmpdir):
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
                    'directories': {
                        "/foo": {},
                        "/foo/bar": {'needs': {"action:"}},
                    },
                },
            },
        },
    )
    stdout, stderr, rcode = run("BW_TABLE_STYLE=grep bw items --attr node1 directory:/foo/bar needs", path=str(tmpdir))
    assert stdout.decode() == """attribute\tvalue
needs\taction:
needs\tdirectory:/foo
"""
    assert stderr.decode() == ""
    assert rcode == 0
