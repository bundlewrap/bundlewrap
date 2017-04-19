from json import loads
from os.path import join

from bundlewrap.utils.testing import make_repo, run


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
    stdout, stderr, rcode = run("bw groups -n", path=str(tmpdir))
    assert stdout == b"""group1: node1
group2: node2, node3
group3: node1, node3
group4: node3
"""
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
    stdout, stderr, rcode = run("bw groups -n", path=str(tmpdir))
    assert stdout == b"""group1: node3, node4
group2: node4
group3: node1, node2, node3, node4
group4: node1, node3, node4
"""
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
    stdout, stderr, rcode = run("bw groups -n", path=str(tmpdir))
    assert stdout == b"""group1: node1
group2: node2
"""
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
    stdout, stderr, rcode = run("bw groups -n", path=str(tmpdir))
    assert stdout == b"""group1: node1, node2
group2: node2
group3: node2
"""
    assert stderr == b""
    assert rcode == 0

    # make sure there is no metadata deadlock
    stdout, stderr, rcode = run("bw metadata node1", path=str(tmpdir))
    assert loads(stdout.decode('utf-8')) == {'remove': False}
    assert stderr == b""
    assert rcode == 0


def test_group_members_removed_from_supergroup(tmpdir):
    make_repo(
        tmpdir,
        nodes={
            'node_in_group': {
                'hostname': "localhost",
            },
            'node_NOT_in_group': {
                'hostname': "localhost",
                'metadata': {
                    'remove_from_group': True,
                },
            },
        },
    )
    with open(join(str(tmpdir), "groups.py"), 'w') as f:
        f.write("""
groups = {
    'super_group': {
        'subgroups': ['intermediate_group'],
    },
    'intermediate_group': {
        'members_remove': lambda node: node.metadata.get('remove_from_group', False),
        'subgroups': ['inner_group'],
    },
    'inner_group': {
        'member_patterns': (
            r".*",
        ),
    },
}
    """)
    stdout, stderr, rcode = run("bw groups -n", path=str(tmpdir))
    assert stdout == b"""inner_group: node_NOT_in_group, node_in_group
intermediate_group: node_in_group
super_group: node_in_group
"""
    assert stderr == b""
    assert rcode == 0
