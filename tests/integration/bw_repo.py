from os import makedirs
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


def test_toml_node_exists_in_new_repo(tmpdir):
    run("bw repo create", path=str(tmpdir))
    makedirs(join(tmpdir, "nodes"))
    with open(join(tmpdir, "nodes", "tomlnode.toml"), 'w') as f:
        f.write("")
    stdout, stderr, rcode = run("bw nodes", path=str(tmpdir))
    assert b"tomlnode" in stdout
    assert stderr == b""
    assert rcode == 0


def test_toml_group_exists_in_new_repo(tmpdir):
    run("bw repo create", path=str(tmpdir))
    makedirs(join(tmpdir, "groups"))
    with open(join(tmpdir, "groups", "tomlgroup.toml"), 'w') as f:
        f.write("")
    stdout, stderr, rcode = run("bw groups", path=str(tmpdir))
    assert b"tomlgroup" in stdout
    assert stderr == b""
    assert rcode == 0

