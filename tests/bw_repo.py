from bundlewrap.utils.testing import run


def test_not_a_repo_test(tmpdir):
    assert run("bw nodes", path=str(tmpdir))[2] == 1
