from os.path import exists, join

from bundlewrap.utils.testing import host_os, make_repo, run


def test_if_succeeds_runs_action(tmpdir):
    marker = join(str(tmpdir), "marker")
    make_repo(
        tmpdir,
        bundles={
            "test": {
                'items': {
                    'actions': {
                        "guarded": {
                            'command': f"touch {marker}",
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
    assert exists(marker)


def test_if_fails_skips_action(tmpdir):
    marker = join(str(tmpdir), "marker")
    make_repo(
        tmpdir,
        bundles={
            "test": {
                'items': {
                    'actions': {
                        "guarded": {
                            'command': f"touch {marker}",
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
    assert not exists(marker)
    # just like with 'unless', these skips are not worth mentioning
    assert b"action:guarded" not in stdout


def test_if_succeeds_fixes_item(tmpdir):
    file = join(str(tmpdir), "file")
    make_repo(
        tmpdir,
        bundles={
            "test": {
                'items': {
                    'files': {
                        file: {
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

    with open(file) as f:
        content = f.read()
    assert content == "1\n"


def test_if_fails_skips_item(tmpdir):
    file = join(str(tmpdir), "file")
    make_repo(
        tmpdir,
        bundles={
            "test": {
                'items': {
                    'files': {
                        file: {
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
    assert not exists(file)


def test_if_fails_does_not_skip_dependents(tmpdir):
    marker = join(str(tmpdir), "marker")
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
                            'command': f"touch {marker}",
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
    assert exists(marker)


def test_if_fails_verify(tmpdir):
    skipped = join(str(tmpdir), "skipped")
    checked = join(str(tmpdir), "checked")
    make_repo(
        tmpdir,
        bundles={
            "test": {
                'items': {
                    'files': {
                        skipped: {
                            'content': "1\n",
                            'if': "false",
                        },
                        checked: {
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
    assert b"unable to get status" not in stderr
    assert f"file:{skipped}".encode() not in stderr
    assert f"file:{checked}".encode() in stderr


def test_if_and_unless_are_mutually_exclusive(tmpdir):
    marker = join(str(tmpdir), "marker")
    make_repo(
        tmpdir,
        bundles={
            "test": {
                'items': {
                    'actions': {
                        "guarded": {
                            'command': f"touch {marker}",
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
    assert not exists(marker)
