from os.path import join

from bundlewrap.utils.testing import make_repo, run


def test_not_a_repo_test(tmpdir):
    assert run("bw nodes", path=str(tmpdir))[2] == 1


def test_subdir_invocation(tmpdir):
    make_repo(tmpdir, nodes={"node1": {}})
    stdout, stderr, rcode = run("bw nodes", path=join(str(tmpdir), "bundles"))
    assert stdout == b"node1\n"
    assert stderr == b""
    assert rcode == 0
