from bundlewrap.utils.testing import make_repo, run


def test_group_members(tmpdir):
    make_repo(
        tmpdir,
        nodes={
            "node1": {},
            "node2": {},
            "node3": {},
        },
        groups={
            "group1": {},
            "group2": {
                'members': {"node2"},
            },
            "group3": {
                'members': {"node2", "node3"},
            },
        },
    )
    stdout, stderr, rcode = run("BW_TABLE_STYLE=grep bw groups -i group1 group2 group3 -a nodes", path=str(tmpdir))
    assert stdout == b"""group1\t
group2\tnode2
group3\tnode2,node3
"""
    assert stderr == b""
    assert rcode == 0


def test_group_members_at_node(tmpdir):
    make_repo(
        tmpdir,
        nodes={
            "node1": {'groups': ["group1", "group2"]},
            "node2": {'groups': ["group1"]},
            "node3": {'groups': []},
        },
        groups={
            "group1": {},
            "group2": {},
            "group3": {},
        },
    )
    stdout, stderr, rcode = run("BW_TABLE_STYLE=grep bw groups -i group1 group2 group3 -a nodes", path=str(tmpdir))
    assert stdout == b"""group1\tnode1,node2
group2\tnode1
group3\t
"""
    assert stderr == b""
    assert rcode == 0
