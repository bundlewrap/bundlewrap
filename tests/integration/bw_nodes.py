from bundlewrap.utils.testing import make_repo, run


def test_empty(tmpdir):
    make_repo(tmpdir)
    stdout, stderr, rcode = run("bw nodes", path=str(tmpdir))
    assert stdout == b""
    assert stderr == b""
    assert rcode == 0


def test_single(tmpdir):
    make_repo(tmpdir, nodes={"node1": {}})
    stdout, stderr, rcode = run("bw nodes", path=str(tmpdir))
    assert stdout == b"node1\n"
    assert stderr == b""
    assert rcode == 0


def test_hostname(tmpdir):
    make_repo(
        tmpdir,
        groups={"all": {'members': ["node1"]}},
        nodes={"node1": {'hostname': "node1.example.com"}},
    )
    stdout, stderr, rcode = run("BW_TABLE_STYLE=grep bw nodes all hostname | cut -f 2", path=str(tmpdir))
    assert stdout == b"node1.example.com\n"
    assert stderr == b""
    assert rcode == 0


def test_bundles(tmpdir):
    make_repo(
        tmpdir,
        bundles={
            "bundle1": {},
            "bundle2": {},
        },
        groups={"all": {'members': ["node1", "node2"]}},
        nodes={
            "node1": {'bundles': ["bundle1", "bundle2"]},
            "node2": {'bundles': ["bundle2"]},
        },
    )
    stdout, stderr, rcode = run("BW_TABLE_STYLE=grep bw nodes all bundles | grep node1 | cut -f 2", path=str(tmpdir))
    assert stdout.decode().strip().split("\n") == ["bundle1", "bundle2"]
    assert stderr == b""
    assert rcode == 0
