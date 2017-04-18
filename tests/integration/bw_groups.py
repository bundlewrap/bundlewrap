from os.path import join

from bundlewrap.utils.testing import make_repo, run


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
