from os.path import exists, join

from bundlewrap.utils.testing import host_os, make_repo, run


def test_after(tmpdir):
    make_repo(
        tmpdir,
        bundles={
            "test": {
                'items': {
                    'actions': {
                        "a": {
                            'command': "echo a >> " + join(str(tmpdir), "foo"),
                            'after': {"action:b"},
                        },
                        "b": {
                            'command': "echo b >> " + join(str(tmpdir), "foo"),
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
    with open(join(str(tmpdir), "foo")) as f:
        assert f.read() == "b\na\n"


def test_before(tmpdir):
    make_repo(
        tmpdir,
        bundles={
            "test": {
                'items': {
                    'actions': {
                        "a": {
                            'command': "echo a >> " + join(str(tmpdir), "foo"),
                            'before': {"action:b"},
                        },
                        "b": {
                            'command': "echo b >> " + join(str(tmpdir), "foo"),
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
    with open(join(str(tmpdir), "foo")) as f:
        assert f.read() == "a\nb\n"


def test_before_fail_no_skip(tmpdir):
    make_repo(
        tmpdir,
        bundles={
            "test": {
                'items': {
                    'actions': {
                        "a": {
                            'command': "false",
                            'before': {"action:b"},
                        },
                        "b": {
                            'command': "echo b >> " + join(str(tmpdir), "foo"),
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
    with open(join(str(tmpdir), "foo")) as f:
        assert f.read() == "b\n"


def test_after_fail_no_skip(tmpdir):
    make_repo(
        tmpdir,
        bundles={
            "test": {
                'items': {
                    'actions': {
                        "a": {
                            'command': "false",
                        },
                        "b": {
                            'after': {"action:a"},
                            'command': "echo b >> " + join(str(tmpdir), "foo"),
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
    with open(join(str(tmpdir), "foo")) as f:
        assert f.read() == "b\n"


def test_before_fail_skip_with_needs(tmpdir):
    make_repo(
        tmpdir,
        bundles={
            "test": {
                'items': {
                    'actions': {
                        "a": {
                            'command': "false",
                            'before': {"action:b"},
                        },
                        "b": {
                            'command': "echo b >> " + join(str(tmpdir), "foo"),
                            'needs': {"action:a"},
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
    assert b"skipped" in stdout
    assert not exists(join(str(tmpdir), "foo"))


def test_after_fail_skip_with_needed_by(tmpdir):
    make_repo(
        tmpdir,
        bundles={
            "test": {
                'items': {
                    'actions': {
                        "a": {
                            'command': "false",
                            'needed_by': {"action:b"},
                        },
                        "b": {
                            'command': "echo b >> " + join(str(tmpdir), "foo"),
                            'after': {"action:a"},
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
    assert b"skipped" in stdout
    assert not exists(join(str(tmpdir), "foo"))


def test_chain_skip(tmpdir):
    make_repo(
        tmpdir,
        bundles={
            "test": {
                'items': {
                    'actions': {
                        "a": {
                            'command': "false",
                        },
                        "b": {
                            'command': "echo b >> " + join(str(tmpdir), "foo"),
                            'needs': {"action:a"},
                        },
                        "c": {
                            'command': "echo c >> " + join(str(tmpdir), "foo"),
                            'after': {"action:b"},
                        },
                        "d": {
                            'command': "echo d >> " + join(str(tmpdir), "foo"),
                            'needs': {"action:b"},
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
    assert b"skipped" in stdout
    with open(join(str(tmpdir), "foo")) as f:
        assert f.read() == "c\n"


def test_chain_skip_no_cascade(tmpdir):
    make_repo(
        tmpdir,
        bundles={
            "test": {
                'items': {
                    'actions': {
                        "a": {
                            'command': "false",
                        },
                        "b": {
                            'command': "echo b >> " + join(str(tmpdir), "foo"),
                            'needs': {"action:a"},
                            'cascade_skip': False,
                        },
                        "c": {
                            'command': "echo c >> " + join(str(tmpdir), "foo"),
                            'after': {"action:b"},
                        },
                        "d": {
                            'command': "echo d >> " + join(str(tmpdir), "foo"),
                            'needs': {"action:b"},
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
    assert b"skipped" in stdout
    with open(join(str(tmpdir), "foo")) as f:
        assert f.read() in ("c\nd\n", "d\nc\n")
