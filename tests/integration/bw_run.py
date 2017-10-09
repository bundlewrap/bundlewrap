from bundlewrap.utils.testing import host_os, make_repo, run


def test_run_ok(tmpdir):
    make_repo(
        tmpdir,
        nodes={
            "localhost": {
                'os': host_os(),
            },
        },
    )
    stdout, stderr, rcode = run("BW_TABLE_STYLE=grep bw run localhost true", path=str(tmpdir))
    assert rcode == 0
    assert b"localhost\t0" in stdout
    assert stderr == b""


def test_run_fail(tmpdir):
    make_repo(
        tmpdir,
        nodes={
            "localhost": {
                'os': host_os(),
            },
        },
    )
    stdout, stderr, rcode = run("BW_TABLE_STYLE=grep bw run localhost false", path=str(tmpdir))
    assert rcode == 0
    assert b"localhost\t1" in stdout
    assert stderr == b""
