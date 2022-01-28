from os.path import join

from bundlewrap.utils.testing import make_repo, run


def test_groups_for_node(tmpdir):
    make_repo(
        tmpdir,
        nodes={
            "node-foo": {'groups': {"group-foo"}},
            "node-bar": {},
            "node-baz": {},
            "node-pop": {'groups': {"group-baz"}},
        },
        groups={
            "group-foo": {
                'member_patterns': [r".*-bar"],
            },
            "group-bar": {
                'subgroups': ["group-foo"],
            },
            "group-baz": {},
            "group-frob": {
                'members': {"node-pop"},
            },
            "group-pop": {
                'subgroup_patterns': [r"ba"],
            },
        },
    )
    stdout, stderr, rcode = run("bw plot groups-for-node node-foo", path=str(tmpdir))
    assert stdout == b"""digraph bundlewrap
{
rankdir = LR
node [color="#303030"; fillcolor="#303030"; fontname=Helvetica]
edge [arrowhead=vee]
"group-bar" [fontcolor=white,style=filled];
"group-foo" [fontcolor=white,style=filled];
"group-pop" [fontcolor=white,style=filled];
"node-foo" [fontcolor="#303030",shape=box,style=rounded];
"group-bar" -> "group-foo" [color="#6BB753",penwidth=2]
"group-foo" -> "node-foo" [color="#D18C57",penwidth=2]
"group-pop" -> "group-bar" [color="#6BB753",penwidth=2]
}
"""
    assert stderr == b""
    assert rcode == 0

    stdout, stderr, rcode = run("bw plot groups-for-node node-pop", path=str(tmpdir))
    assert stdout == b"""digraph bundlewrap
{
rankdir = LR
node [color="#303030"; fillcolor="#303030"; fontname=Helvetica]
edge [arrowhead=vee]
"group-baz" [fontcolor=white,style=filled];
"group-frob" [fontcolor=white,style=filled];
"group-pop" [fontcolor=white,style=filled];
"node-pop" [fontcolor="#303030",shape=box,style=rounded];
"group-baz" -> "node-pop" [color="#D18C57",penwidth=2]
"group-frob" -> "node-pop" [color="#D18C57",penwidth=2]
"group-pop" -> "group-baz" [color="#6BB753",penwidth=2]
}
"""
    assert stderr == b""
    assert rcode == 0


def test_empty_tags(tmpdir):
    make_repo(
        tmpdir,
        nodes={
            "node1": {
                'bundles': ["bundle1"],
            },
        },
        bundles={
            "bundle1": {
                'attrs': {
                    'tags': {
                        "empty": {
                            'needs': {"action:early"},
                        },
                    },
                },
                'items': {
                    'actions': {
                        "early": {
                            'command': "true",
                        },
                        "late": {
                            'command': "true",
                            'needs': {"tag:empty"},
                        },
                    },
                },
            },
        },
    )
    stdout, stderr, rcode = run("bw plot node node1", path=str(tmpdir))
    assert rcode == 0
    assert '"action:late" -> "empty_tag:empty"' in stdout.decode()
    assert '"empty_tag:empty" -> "action:early"' in stdout.decode()


def test_no_empty_tags(tmpdir):
    make_repo(
        tmpdir,
        nodes={
            "node1": {
                'bundles': ["bundle1"],
            },
        },
        bundles={
            "bundle1": {
                'attrs': {
                    'tags': {
                        "notempty": {
                            'needs': {"action:early"},
                        },
                    },
                },
                'items': {
                    'actions': {
                        "early": {
                            'command': "true",
                        },
                        "middle": {
                            'command': "true",
                            'tags': {"notempty"},
                        },
                        "late": {
                            'command': "true",
                            'needs': {"tag:notempty"},
                        },
                    },
                },
            },
        },
    )
    stdout, stderr, rcode = run("bw plot node node1", path=str(tmpdir))
    assert rcode == 0
    assert '"action:late" -> "action:middle"' in stdout.decode()
    assert '"action:middle" -> "action:early"' in stdout.decode()
    assert "empty_tag" not in stdout.decode()


def test_plot_reactors(tmpdir):
    make_repo(
        tmpdir,
        bundles={"test": {}},
        nodes={
            "node1": {
                'bundles': ["test"],
            },
        },
    )
    with open(join(str(tmpdir), "bundles", "test", "metadata.py"), 'w') as f:
        f.write(
"""
@metadata_reactor.provides('foo')
def reactor1(metadata):
    return {'foo': metadata.get('bar')}

@metadata_reactor.provides('bar')
def reactor2(metadata):
    return {'bar': 47}
""")
    stdout, stderr, rcode = run("bw plot reactors node1", path=str(tmpdir))
    assert rcode == 0
    assert "reactor1" in stdout.decode()
