from json import loads
from os.path import join

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
    make_repo(tmpdir, nodes={"node1": {'hostname': "node1.example.com"}})
    stdout, stderr, rcode = run("bw nodes --attrs | grep '\thostname' | cut -f 3", path=str(tmpdir))
    assert stdout == b"node1.example.com\n"
    assert stderr == b""
    assert rcode == 0


def test_inline(tmpdir):
    make_repo(
        tmpdir,
        nodes={
            "node1": {
                'bundles': ["bundle1", "bundle2"],
            },
            "node2": {
                'bundles': ["bundle1"],
            },
        },
        bundles={
            "bundle1": {},
            "bundle2": {},
        },
    )
    stdout, stderr, rcode = run("bw nodes -ai | grep '\tbundle' | grep bundle2 | cut -f 1", path=str(tmpdir))
    assert stdout == b"node1\n"
    assert stderr == b""
    assert rcode == 0

    stdout, stderr, rcode = run("bw nodes -ai | grep '\tbundle' | grep -v bundle2 | cut -f 1", path=str(tmpdir))
    assert stdout == b"node2\n"
    assert stderr == b""
    assert rcode == 0


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
    assert rcode == 0


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
    assert rcode == 0


def test_groups(tmpdir):
    make_repo(
        tmpdir,
        groups={
            "group1": {
                'members': ["node2"],
            },
            "group2": {
                'members': ["node1"],
            },
            "group3": {
                'subgroup_patterns': ["p2"],
            },
            "group4": {
                'subgroups': ["group1"],
            },
        },
        nodes={
            "node1": {},
            "node2": {},
        },
    )
    stdout, stderr, rcode = run("bw nodes --groups", path=str(tmpdir))
    assert stdout.decode().strip().split("\n") == [
        "node1: group2, group3",
        "node2: group1, group4",
    ]
    assert stderr == b""
    assert rcode == 0


def test_group_members_add(tmpdir):
    make_repo(
        tmpdir,
        nodes={
            "node1": {'os': 'centos'},
            "node2": {'os': 'debian'},
            "node3": {'os': 'ubuntu'},
        },
    )
    with open(join(str(tmpdir), "groups.py"), 'w') as f:
        f.write("""
groups = {
    "group1": {
        'members_add': lambda node: node.os == 'centos',
    },
    "group2": {
        'members': ["node2"],
        'members_add': lambda node: node.os != 'centos',
    },
    "group3": {
        'members_add': lambda node: not node.in_group("group2"),
    },
    "group4": {
        'members': ["node3"],
    },
}
    """)
    stdout, stderr, rcode = run("bw nodes -a node1 | grep \tgroup | cut -f 3", path=str(tmpdir))
    assert stdout == b"group1\ngroup3\n"
    assert stderr == b""
    assert rcode == 0

    stdout, stderr, rcode = run("bw nodes -a node2 | grep \tgroup | cut -f 3", path=str(tmpdir))
    assert stdout == b"group2\n"
    assert stderr == b""
    assert rcode == 0

    stdout, stderr, rcode = run("bw nodes -a node3 | grep \tgroup | cut -f 3", path=str(tmpdir))
    assert stdout == b"group2\ngroup3\ngroup4\n"
    assert stderr == b""
    assert rcode == 0


def test_group_members_remove(tmpdir):
    make_repo(
        tmpdir,
        nodes={
            "node1": {'os': 'centos'},
            "node2": {'os': 'debian'},
            "node3": {'os': 'ubuntu'},
            "node4": {'os': 'ubuntu'},
        },
    )
    with open(join(str(tmpdir), "groups.py"), 'w') as f:
        f.write("""
groups = {
    "group1": {
        'members_add': lambda node: node.os == 'ubuntu',
    },
    "group2": {
        'members_add': lambda node: node.os == 'ubuntu',
        'members_remove': lambda node: node.name == "node3",
    },
    "group3": {
        'members_add': lambda node: not node.in_group("group3"),
    },
    "group4": {
        'subgroups': ["group3"],
        'members_remove': lambda node: node.os == 'debian',
    },
}
    """)
    stdout, stderr, rcode = run("bw nodes -a node1 | grep \tgroup | cut -f 3", path=str(tmpdir))
    assert stdout == b"group3\ngroup4\n"
    assert stderr == b""
    assert rcode == 0

    stdout, stderr, rcode = run("bw nodes -a node2 | grep \tgroup | cut -f 3", path=str(tmpdir))
    assert stdout == b"group3\n"
    assert stderr == b""
    assert rcode == 0

    stdout, stderr, rcode = run("bw nodes -a node3 | grep \tgroup | cut -f 3", path=str(tmpdir))
    assert stdout == b"group1\ngroup3\ngroup4\n"
    assert stderr == b""
    assert rcode == 0

    stdout, stderr, rcode = run("bw nodes -a node4 | grep \tgroup | cut -f 3", path=str(tmpdir))
    assert stdout == b"group1\ngroup2\ngroup3\ngroup4\n"
    assert stderr == b""
    assert rcode == 0


def test_group_members_remove_bundle(tmpdir):
    make_repo(
        tmpdir,
        bundles={
            "bundle1": {},
            "bundle2": {},
        },
        nodes={
            "node1": {},
            "node2": {},
        },
    )
    with open(join(str(tmpdir), "groups.py"), 'w') as f:
        f.write("""
groups = {
    "group1": {
        'bundles': ["bundle1"],
        'members': ["node1", "node2"],
    },
    "group2": {
        'bundles': ["bundle1", "bundle2"],
        'members': ["node1", "node2"],
        'members_remove': lambda node: node.name == "node2",
    },
}
    """)
    stdout, stderr, rcode = run("bw nodes -a node1 | grep \tbundle | cut -f 3", path=str(tmpdir))
    assert stdout == b"bundle1\nbundle2\n"
    assert stderr == b""
    assert rcode == 0

    stdout, stderr, rcode = run("bw nodes -a node2 | grep \tbundle | cut -f 3", path=str(tmpdir))
    assert stdout == b"bundle1\n"
    assert stderr == b""
    assert rcode == 0


def test_group_members_partial_metadata(tmpdir):
    make_repo(
        tmpdir,
        nodes={
            "node1": {
                'metadata': {'foo': 1},
            },
            "node2": {},
        },
    )
    with open(join(str(tmpdir), "groups.py"), 'w') as f:
        f.write("""
groups = {
    "group1": {
        'members_add': lambda node: node.metadata.get('foo') == 1,
    },
    "group2": {
        'members': ["node2"],
        'metadata': {'foo': 1},
    },
}
    """)
    stdout, stderr, rcode = run("bw nodes -a node1 | grep \tgroup | cut -f 3", path=str(tmpdir))
    assert stdout == b"group1\n"
    assert stderr == b""
    assert rcode == 0

    stdout, stderr, rcode = run("bw nodes -a node2 | grep \tgroup | cut -f 3", path=str(tmpdir))
    assert stdout == b"group2\n"
    assert stderr == b""
    assert rcode == 0


def test_group_members_remove_based_on_metadata(tmpdir):
    make_repo(
        tmpdir,
        nodes={
            "node1": {
                'metadata': {'remove': False},
            },
            "node2": {},
        },
    )
    with open(join(str(tmpdir), "groups.py"), 'w') as f:
        f.write("""
groups = {
    "group1": {
        'members_add': lambda node: not node.metadata.get('remove', False),
        'members_remove': lambda node: node.metadata.get('remove', False),
    },
    "group2": {
        'members': ["node2"],
        'metadata': {'remove': True},
    },
    "group3": {
        'subgroups': ["group1"],
        'members_remove': lambda node: node.name.endswith("1") and node.metadata.get('redherring', True),
    },
}
    """)
    stdout, stderr, rcode = run("bw nodes -a node1 | grep \tgroup | cut -f 3", path=str(tmpdir))
    assert stdout == b"group1\n"
    assert stderr == b""
    assert rcode == 0

    stdout, stderr, rcode = run("bw nodes -a node2 | grep \tgroup | cut -f 3", path=str(tmpdir))
    assert stdout == b"group1\ngroup2\ngroup3\n"
    assert stderr == b""
    assert rcode == 0

    # make sure there is no metadata deadlock
    stdout, stderr, rcode = run("bw metadata node1", path=str(tmpdir))
    assert loads(stdout.decode('utf-8')) == {'remove': False}
    assert stderr == b""
    assert rcode == 0
