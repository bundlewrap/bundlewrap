from os.path import join

from bundlewrap.utils.testing import make_repo, run


def test_empty(tmpdir):
    make_repo(tmpdir)
    stdout, stderr, rcode = run("bw hash", path=str(tmpdir))
    assert stdout == b"44136fa355b3678a1146ad16f7e8649e94fb4fc21fe77e8310c060f61caaff8a\n"
    assert stderr == b""
    assert rcode == 0


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
        assert rcode == 0
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
        assert rcode == 0
        hashes.add(stdout.strip())

    assert len(hashes) == 1
    assert hashes.pop() == b"d971ecd41722ad194e1d0ea3a5edacbcdf3b73d91c7c32302ce04c10b0705a7e"


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
                    'actions': {
                        "test": {
                            'command': "true",
                        },
                    },
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
    assert stdout == b"e5ce2bede00e9edffa8f907f3bd6ddabc10e139ffa6c50719f46504f56bb4b9b  node1\n"

    stdout, stderr, rcode = run("bw hash -d node1", path=str(tmpdir))
    assert rcode == 0
    assert stdout == b"867841c209f2d269c5d395c5d2da55473e40c8e44a4c4fb4696e27c3f3e80e71  file:/test\n"

    stdout, stderr, rcode = run("bw hash -d node1 file:/test", path=str(tmpdir))
    assert rcode == 0
    assert stdout == (
        b"content_hash\t780f94dcf198f04a230c62fb135297eb3c37c9eb26c84d635ade85202789124c\n"
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
    assert stdout == b"44136fa355b3678a1146ad16f7e8649e94fb4fc21fe77e8310c060f61caaff8a\n"


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
    assert stdout1 == b"dc8aeb53a7175923f49f13a11b86f112634ffba5448f62f0fae6c01d12e67e6b\n"
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
    assert stdout1 == b"170200f5473a004c65fe1a87a12acb780533d571c990356e8aa02af8f690a08b\n"

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
    assert stdout == b"ff615a780a9181299ede59c07aed913fc4c7db0691fac7e2fbf54a7881f9051d\n"


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
    assert stdout == b"node1\t51a11939dfc74a376361fd5dae8f40ed27243ee9d1f9133a7aa2e76a1e920964\n"


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
    assert stdout == b"4fa6b006dce70008589915bdd008036e35a847131cdd2da98e6be585306e9e78\n"


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
    assert stdout == b"763ba79953798760239be7150fd656e131df56b24ebbd4daec7b7c66ef27f993\n"


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
    assert stdout == b"af67656b03c0e90bd3f900de3bbed794811185202bf9f996d78e3d2e550fd477\n"


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
