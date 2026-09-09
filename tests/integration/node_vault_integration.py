from os import makedirs
from os.path import join

from bundlewrap.utils.testing import make_repo, run


def _attrs(tmpdir):
    stdout, stderr, rcode = run(
        "BW_TABLE_STYLE=grep bw nodes -a generate_key encrypt_key",
        path=str(tmpdir),
    )
    assert stderr == b""
    assert rcode == 0
    return {
        line.split("\t")[0]: line.split("\t")[1:]
        for line in stdout.decode().strip().split("\n")
    }


def test_key_attrs_from_groups(tmpdir):
    make_repo(
        tmpdir,
        groups={
            "group1": {"generate_key": "gen-group", "encrypt_key": "enc-group"},
        },
        nodes={
            "node1": {"groups": ["group1"]},
            "node2": {"groups": ["group1"], "generate_key": "gen-node"},
            "node3": {},
        },
    )
    rows = _attrs(tmpdir)
    assert rows["node1"] == ["gen-group", "enc-group"]
    assert rows["node2"] == ["gen-node", "enc-group"]
    assert rows["node3"] == ["None", "None"]


def test_key_attrs_in_toml(tmpdir):
    make_repo(tmpdir)
    makedirs(join(tmpdir, "groups"))
    with open(join(tmpdir, "groups", "group1.toml"), 'w') as f:
        f.write('members = ["node1"]\ngenerate_key = "gen-group"\nencrypt_key = "enc-group"\n')
    makedirs(join(tmpdir, "nodes"))
    with open(join(tmpdir, "nodes", "node1.toml"), 'w') as f:
        f.write("")
    with open(join(tmpdir, "nodes", "node2.toml"), 'w') as f:
        f.write('generate_key = "gen-node"\nencrypt_key = "enc-node"\n')
    rows = _attrs(tmpdir)
    assert rows["node1"] == ["gen-group", "enc-group"]
    assert rows["node2"] == ["gen-node", "enc-node"]
