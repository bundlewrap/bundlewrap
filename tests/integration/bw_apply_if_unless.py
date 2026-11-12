from os.path import exists, join

from bundlewrap.utils.testing import host_os, make_repo, run


def test_if_succeeds_runs_action(tmpdir):
    make_repo(
        tmpdir,
        bundles={
            "test": {
                'items': {
                    'actions': {
                        "guarded": {
                            'command': "touch {}".format(join(str(tmpdir), "marker")),
                            'if': "true",
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
    stdout, stderr, rcode = run("bw apply localhost", path=str(tmpdir))
    assert rcode == 0
    assert exists(join(str(tmpdir), "marker"))


def test_if_fails_skips_action(tmpdir):
    make_repo(
        tmpdir,
        bundles={
            "test": {
                'items': {
                    'actions': {
                        "guarded": {
                            'command': "touch {}".format(join(str(tmpdir), "marker")),
                            'if': "false",
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
    stdout, stderr, rcode = run("bw apply localhost", path=str(tmpdir))
    assert rcode == 0
    assert not exists(join(str(tmpdir), "marker"))
    # just like with 'unless', these skips are not worth mentioning
    assert b"action:guarded" not in stdout


def test_if_succeeds_fixes_item(tmpdir):
    make_repo(
        tmpdir,
        bundles={
            "test": {
                'items': {
                    'files': {
                        join(str(tmpdir), "file"): {
                            'content': "1\n",
                            'if': "true",
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
    stdout, stderr, rcode = run("bw apply localhost", path=str(tmpdir))
    assert rcode == 0

    with open(join(str(tmpdir), "file")) as f:
        content = f.read()
    assert content == "1\n"


def test_if_fails_skips_item(tmpdir):
    make_repo(
        tmpdir,
        bundles={
            "test": {
                'items': {
                    'files': {
                        join(str(tmpdir), "file"): {
                            'content': "1\n",
                            'if': "false",
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
    stdout, stderr, rcode = run("bw apply localhost", path=str(tmpdir))
    assert rcode == 0
    assert not exists(join(str(tmpdir), "file"))


def test_if_fails_does_not_skip_dependents(tmpdir):
    make_repo(
        tmpdir,
        bundles={
            "test": {
                'items': {
                    'actions': {
                        "guarded": {
                            'command': "true",
                            'if': "false",
                        },
                        "dependent": {
                            'command': "touch {}".format(join(str(tmpdir), "marker")),
                            'needs': ["action:guarded"],
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
    stdout, stderr, rcode = run("bw apply localhost", path=str(tmpdir))
    assert rcode == 0
    assert exists(join(str(tmpdir), "marker"))


def test_if_fails_verify(tmpdir):
    make_repo(
        tmpdir,
        bundles={
            "test": {
                'items': {
                    'files': {
                        join(str(tmpdir), "skipped"): {
                            'content': "1\n",
                            'if': "false",
                        },
                        join(str(tmpdir), "checked"): {
                            'content': "1\n",
                            'if': "true",
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
    stdout, stderr, rcode = run("bw verify localhost", path=str(tmpdir))
    assert rcode == 0
    assert "file:{}".format(join(str(tmpdir), "skipped")).encode() not in stderr
    assert "file:{}".format(join(str(tmpdir), "checked")).encode() in stderr


def test_if_and_unless_are_mutually_exclusive(tmpdir):
    make_repo(
        tmpdir,
        bundles={
            "test": {
                'items': {
                    'actions': {
                        "guarded": {
                            'command': "touch {}".format(join(str(tmpdir), "marker")),
                            'if': "true",
                            'unless': "false",
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
    stdout, stderr, rcode = run("bw apply localhost", path=str(tmpdir))
    assert rcode == 1
    assert b"can't use both 'if' and 'unless'" in stderr
    assert not exists(join(str(tmpdir), "marker"))
