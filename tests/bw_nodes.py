from bundlewrap.utils.testing import make_repo, run


def test_empty(tmpdir):
    make_repo(tmpdir)
    stdout, stderr, rcode = run("bw nodes", path=str(tmpdir))
    assert stdout == b""
    assert stderr == b""


def test_single(tmpdir):
    make_repo(tmpdir, nodes={"node1": {}})
    stdout, stderr, rcode = run("bw nodes", path=str(tmpdir))
    assert stdout == b"node1\n"
    assert stderr == b""


def test_hostname(tmpdir):
    make_repo(tmpdir, nodes={"node1": {'hostname': "node1.example.com"}})
    stdout, stderr, rcode = run("bw nodes --attrs | cut -f 2 | cut -d ' ' -f 2", path=str(tmpdir))
    assert stdout == b"hostname:node1.example.com\n"
    assert stderr == b""


def test_in_group(tmpdir):
    make_repo(
        tmpdir,
        groups={
            "group1": {
                'members': ["node2"],
            },
        },
        nodes={
            "node1": {},
            "node2": {},
        },
    )
    stdout, stderr, rcode = run("bw nodes -g group1", path=str(tmpdir))
    assert stdout == b"node2\n"
    assert stderr == b""


def test_bundles(tmpdir):
    make_repo(
        tmpdir,
        bundles={
            "bundle1": {},
            "bundle2": {},
        },
        nodes={
            "node1": {'bundles': ["bundle1", "bundle2"]},
            "node2": {'bundles': ["bundle2"]},
        },
    )
    stdout, stderr, rcode = run("bw nodes --bundles", path=str(tmpdir))
    assert stdout.decode().strip().split("\n") == [
        "node1: bundle1, bundle2",
        "node2: bundle2",
    ]
    assert stderr == b""


def test_groups(tmpdir):
    make_repo(
        tmpdir,
        groups={
            "group1": {
                'members': ["node2"],
            },
        },
        nodes={
            "node1": {},
            "node2": {},
        },
    )
    stdout, stderr, rcode = run("bw nodes --groups", path=str(tmpdir))
    assert stdout.decode().strip().split("\n") == [
        "node1: ",
        "node2: group1",
    ]
    assert stderr == b""
