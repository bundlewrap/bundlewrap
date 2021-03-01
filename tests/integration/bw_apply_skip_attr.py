from os.path import exists, join

from bundlewrap.utils.testing import host_os, make_repo, run


def test_skip_attr_no_cascade(tmpdir):
    make_repo(
        tmpdir,
        bundles={
            "test": {
                'items': {
                    'files': {
                        join(str(tmpdir), "foo"): {
                            'content': "nope",
                            'skip': True,
                        },
                        join(str(tmpdir), "bar"): {
                            'content': "yes",
                            'needs': {"file:" + join(str(tmpdir), "foo")},
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
    assert not exists(join(str(tmpdir), "foo"))
    assert exists(join(str(tmpdir), "bar"))
    assert b"attribute" in stdout


def test_skip_attr_action(tmpdir):
    make_repo(
        tmpdir,
        bundles={
            "test": {
                'items': {
                    'actions': {
                        "foo": {
                            'command': "true",
                            'skip': True,
                        },
                        "bar": {
                            'command': "true",
                            'needs': {"action:foo"},
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
    assert b"succeeded" in stdout
    assert b"attribute" in stdout
