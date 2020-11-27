from bundlewrap.utils.testing import make_repo, run


def test_metadata(tmpdir):
    make_repo(
        tmpdir,
        nodes={
            "node1": {'metadata': {"key": "value1"}},
            "node2": {'metadata': {"key": "value2"}},
        },
    )
    stdout, stderr, rcode = run("bw diff -m node1 node2", path=str(tmpdir))
    assert b"value1" in stdout
    assert b"value2" in stdout
    assert stderr == b""
    assert rcode == 0


def test_file_items(tmpdir):
    make_repo(
        tmpdir,
        nodes={
            "node1": {'bundles': ["bundle1"]},
            "node2": {'bundles': ["bundle2"]},
        },
        bundles={
            "bundle1": {
                'items': {
                    "files": {
                        "/tmp/test": {
                            'content': "one",
                        },
                    },
                },
            },
            "bundle2": {
                'items': {
                    "files": {
                        "/tmp/test": {
                            'content': "two",
                        },
                    },
                },
            },
        },
    )
    stdout, stderr, rcode = run("bw diff -i file:/tmp/test -- node1 node2", path=str(tmpdir))
    assert b"one" in stdout
    assert b"two" in stdout
    assert stderr == b""
    assert rcode == 0


def test_whole_node(tmpdir):
    make_repo(
        tmpdir,
        nodes={
            "node1": {'bundles': ["bundle1", "bundle3"]},
            "node2": {'bundles': ["bundle2", "bundle3"]},
        },
        bundles={
            "bundle1": {
                'items': {
                    "files": {
                        "/tmp/foo": {
                            'content': "one",
                        },
                    },
                },
            },
            "bundle2": {
                'items': {
                    "files": {
                        "/tmp/foo": {
                            'content': "two",
                        },
                    },
                },
            },
            "bundle3": {
                'items': {
                    "files": {
                        "/tmp/bar": {
                            'content': "common",
                        },
                    },
                },
            },
        },
    )
    stdout, stderr, rcode = run("bw diff node1 node2", path=str(tmpdir))
    assert b"/tmp/foo" in stdout
    assert b"/tmp/bar" not in stdout
    assert stderr == b""
    assert rcode == 0
