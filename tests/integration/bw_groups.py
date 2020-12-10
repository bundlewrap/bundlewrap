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


def test_supergroups(tmpdir):
    make_repo(
        tmpdir,
        groups={
            "group1": {},
            "group2": {'supergroups': {"group1"}},
            "group3": {'supergroups': {"group1"}},
            "group4": {},
            "group5": {'subgroups': {"group1"}},
        },
    )
    stdout, stderr, rcode = run("BW_TABLE_STYLE=grep bw groups group1", path=str(tmpdir))
    assert stdout == b"""group1
group2
group3
"""
    assert stderr == b""
    assert rcode == 0

    stdout, stderr, rcode = run("BW_TABLE_STYLE=grep bw groups group2", path=str(tmpdir))
    assert stdout == b"group2\n"
    assert stderr == b""
    assert rcode == 0


def test_supergroups_indirect(tmpdir):
    make_repo(
        tmpdir,
        groups={
            "group1": {},
            "group2": {'supergroups': {"group1"}},
            "group3": {'supergroups': {"group2"}},
            "group4": {},
            "group5": {'subgroups': {"group1"}},
        },
    )
    stdout, stderr, rcode = run("BW_TABLE_STYLE=grep bw groups group1", path=str(tmpdir))
    assert stdout == b"""group1
group2
group3
"""
    assert stderr == b""
    assert rcode == 0

    stdout, stderr, rcode = run("BW_TABLE_STYLE=grep bw groups group2", path=str(tmpdir))
    assert stdout == b"""group2
group3
"""
    assert stderr == b""
    assert rcode == 0


def test_supergroups_loop(tmpdir):
    make_repo(
        tmpdir,
        groups={
            "group1": {'supergroups': {"group2"}},
            "group2": {'supergroups': {"group1"}},
            "group3": {},
        },
    )
    stdout, stderr, rcode = run("BW_TABLE_STYLE=grep bw groups group1", path=str(tmpdir))
    assert b"group1" in stderr
    assert b"group2" in stderr
    assert b"group3" not in stderr
    assert rcode == 1


def test_supergroups_loop_thru_subgroup(tmpdir):
    make_repo(
        tmpdir,
        groups={
            "group1": {
                'subgroups': {"group2"},
                'supergroups': {"group3"},
            },
            "group2": {'subgroups': {"group3"}},
            "group3": {},
            "group4": {},
        },
    )
    stdout, stderr, rcode = run("BW_TABLE_STYLE=grep bw groups group1", path=str(tmpdir))
    assert b"group1" in stderr
    assert b"group2" in stderr
    assert b"group3" in stderr
    assert b"group4" not in stderr
    assert rcode == 1


def test_supergroups_redundant(tmpdir):
    make_repo(
        tmpdir,
        groups={
            "group1": {'subgroups': {"group2"}},
            "group2": {'supergroups': {"group1"}},
            "group3": {},
        },
    )
    stdout, stderr, rcode = run("BW_TABLE_STYLE=grep bw groups group1", path=str(tmpdir))
    assert b"group1" in stderr
    assert b"group2" in stderr
    assert b"group3" not in stderr
    assert rcode == 1
