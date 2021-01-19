from os.path import join

from bundlewrap.utils.testing import make_repo, run


def test_empty(tmpdir):
    make_repo(tmpdir)
    stdout, stderr, rcode = run("bw hash", path=str(tmpdir))
    assert stdout == b"bf21a9e8fbc5a3846fb05b4fa0859e0917b2202f\n"
    assert stderr == b""


def test_nondeterministic(tmpdir):
    make_repo(
        tmpdir,
        nodes={
            "node1": {
                'bundles': ["bundle1"],
            },
        },
        bundles={
            "bundle1": {
                'items': {
                    'files': {
                        "/test": {
                            'content_type': 'mako',
                            'content': "<% import random %>${random.randint(1, 9999)}",
                        },
                    },
                },
            },
        },
    )

    hashes = set()

    for i in range(3):
        stdout, stderr, rcode = run("bw hash", path=str(tmpdir))
        hashes.add(stdout.strip())

    assert len(hashes) > 1


def test_deterministic(tmpdir):
    make_repo(
        tmpdir,
        nodes={
            "node1": {
                'bundles': ["bundle1"],
            },
        },
        bundles={
            "bundle1": {
                'items': {
                    'files': {
                        "/test": {
                            'content': "${node.name}",
                            'group': None,  # BSD has a different default and we don't want to
                                            # deal with that here
                        },
                    },
                },
            },
        },
    )

    hashes = set()

    for i in range(3):
        stdout, stderr, rcode = run("bw hash", path=str(tmpdir))
        hashes.add(stdout.strip())

    assert len(hashes) == 1
    assert hashes.pop() == b"2203e7acc35608bbff471c023b7b7498e5b385d9"


def test_dict(tmpdir):
    make_repo(
        tmpdir,
        nodes={
            "node1": {
                'bundles': ["bundle1"],
            },
        },
        bundles={
            "bundle1": {
                'items': {
                    'files': {
                        "/test": {
                            'content': "yes please",
                            'group': None,  # BSD has a different default and we don't want to
                                            # deal with that here
                        },
                    },
                },
            },
        },
    )

    stdout, stderr, rcode = run("bw hash -d", path=str(tmpdir))
    assert rcode == 0
    assert stdout == b"93e7a2c6e8cdc71fb4df5426bc0d0bb978d84381  node1\n"

    stdout, stderr, rcode = run("bw hash -d node1", path=str(tmpdir))
    assert rcode == 0
    assert stdout == b"59d1a7c79640ccdfd3700ab141698a9389fcd0b7  file:/test\n"

    stdout, stderr, rcode = run("bw hash -d node1 file:/test", path=str(tmpdir))
    assert rcode == 0
    assert stdout == (
        b"content_hash\tc05a36d547e2b1682472f76985018038d1feebc5\n"
        b"mode\t0644\n"
        b"owner\troot\n"
        b"type\tfile\n"
    )


def test_metadata_empty(tmpdir):
    make_repo(
        tmpdir,
        nodes={
            "node1": {
                'metadata': {},
            },
        },
    )

    stdout, stderr, rcode = run("bw hash -m node1", path=str(tmpdir))
    assert rcode == 0
    assert stdout == b"bf21a9e8fbc5a3846fb05b4fa0859e0917b2202f\n"


def test_metadata_fault(tmpdir):
    make_repo(tmpdir)
    with open(join(str(tmpdir), "nodes.py"), 'w') as f:
        f.write("""
nodes = {
    'node1': {
        'metadata': {'foo': vault.password_for("testing")},
    },
    'node2': {
        'metadata': {'foo': vault.password_for("testing").value},
    },
    'node3': {
        'metadata': {'foo': "faCTT76kagtDuZE5wnoiD1CxhGKmbgiX"},
    },
    'node4': {
        'metadata': {'foo': "something else entirely"},
    },
}
""")
    stdout1, stderr, rcode = run("bw hash -m node1", path=str(tmpdir))
    assert stdout1 == b"b60c0959c9c1ff38940d7b6d4121b2162be34fc9\n"
    assert stderr == b""
    assert rcode == 0
    stdout2, stderr, rcode = run("bw hash -m node2", path=str(tmpdir))
    assert stdout2 == stdout1
    assert stderr == b""
    assert rcode == 0
    stdout3, stderr, rcode = run("bw hash -m node3", path=str(tmpdir))
    assert stdout3 == stdout1
    assert stderr == b""
    assert rcode == 0
    stdout4, stderr, rcode = run("bw hash -m node4", path=str(tmpdir))
    assert stdout4 != stdout1
    assert stderr == b""
    assert rcode == 0


def test_metadata_nested_sort(tmpdir):
    make_repo(
        tmpdir,
        nodes={
            "node1": {
                'metadata': {
                    'nested': {
                        'one': True,
                        'two': False,
                        'three': 3,
                        'four': "four",
                        'five': None,
                    },
                },
            },
            "node2": {
                'metadata': {
                    'nested': {
                        'five': None,
                        'four': "four",
                        'one': True,
                        'three': 3,
                        'two': False,
                    },
                },
            },
        },
    )

    stdout1, stderr, rcode = run("bw hash -m node1", path=str(tmpdir))
    assert rcode == 0
    assert stdout1 == b"d96dc8da8948d0da7924954a657ac960ce7194e9\n"

    stdout2, stderr, rcode = run("bw hash -m node2", path=str(tmpdir))
    assert rcode == 0
    assert stdout1 == stdout2


def test_metadata_repo(tmpdir):
    make_repo(
        tmpdir,
        nodes={
            "node1": {
                'metadata': {
                    'foo': 47,
                },
            },
        },
    )

    stdout, stderr, rcode = run("bw hash -m", path=str(tmpdir))
    assert rcode == 0
    assert stdout == b"8c4a30eaa521c966c678d6e51070f6b3a34b7322\n"


def test_metadata_repo_dict(tmpdir):
    make_repo(
        tmpdir,
        nodes={
            "node1": {
                'metadata': {
                    'foo': 47,
                },
            },
        },
    )

    stdout, stderr, rcode = run("bw hash -md", path=str(tmpdir))
    assert rcode == 0
    assert stdout == b"node1\t223fb72805ecab20f92b463af65896303f997f1c\n"


def test_groups_repo(tmpdir):
    make_repo(
        tmpdir,
        groups={
            "group1": {},
            "group2": {},
        },
    )

    stdout, stderr, rcode = run("bw hash -g", path=str(tmpdir))
    assert rcode == 0
    assert stdout == b"479c737e191339e5fae20ac8a8903a75f6b91f4d\n"


def test_groups_repo_dict(tmpdir):
    make_repo(
        tmpdir,
        groups={
            "group1": {},
            "group2": {},
        },
    )

    stdout, stderr, rcode = run("bw hash -dg", path=str(tmpdir))
    assert rcode == 0
    assert stdout == b"group1\ngroup2\n"


def test_groups(tmpdir):
    make_repo(
        tmpdir,
        groups={
            "group1": {'members': ["node1", "node2"]},
            "group2": {'members': ["node3"]},
        },
        nodes={
            "node1": {},
            "node2": {},
            "node3": {},
        },
    )

    stdout, stderr, rcode = run("bw hash -g group1", path=str(tmpdir))
    assert rcode == 0
    assert stdout == b"59f5a812acd22592b046b20e9afedc1cfcd37c77\n"


def test_groups_dict(tmpdir):
    make_repo(
        tmpdir,
        groups={
            "group1": {},
            "group2": {},
        },
        nodes={
            "node1": {'groups': {"group1"}},
            "node2": {'groups': {"group1"}},
            "node3": {'groups': {"group2"}},
        },
    )

    stdout, stderr, rcode = run("bw hash -dg group1", path=str(tmpdir))
    assert rcode == 0
    assert stdout == b"node1\nnode2\n"


def test_groups_node(tmpdir):
    make_repo(
        tmpdir,
        groups={
            "group1": {},
            "group2": {},
        },
        nodes={
            "node1": {'groups': {"group1"}},
            "node2": {'groups': {"group1"}},
            "node3": {'groups': {"group2"}},
        },
    )

    stdout, stderr, rcode = run("bw hash -g node1", path=str(tmpdir))
    assert rcode == 0
    assert stdout == b"6f4615dc71426549e22df7961bd2b88ba95ad1fc\n"


def test_groups_node_dict(tmpdir):
    make_repo(
        tmpdir,
        groups={
            "group1": {},
            "group2": {},
        },
        nodes={
            "node1": {'groups': {"group1"}},
            "node2": {'groups': {"group1"}},
            "node3": {'groups': {"group2"}},
        },
    )

    stdout, stderr, rcode = run("bw hash -dg node1", path=str(tmpdir))
    assert rcode == 0
    assert stdout == b"group1\n"
