from json import loads
from os.path import join

from bundlewrap.utils.testing import make_repo, run


def test_empty(tmpdir):
    make_repo(
        tmpdir,
        nodes={
            "node1": {},
        },
    )
    stdout, stderr, rcode = run("bw metadata node1", path=str(tmpdir))
    assert stdout == b"{}\n"
    assert stderr == b""
    assert rcode == 0


def test_simple(tmpdir):
    make_repo(
        tmpdir,
        nodes={
            "node1": {'metadata': {"foo": "bar"}},
        },
    )
    stdout, stderr, rcode = run("bw metadata node1", path=str(tmpdir))
    assert loads(stdout.decode()) == {"foo": "bar"}
    assert stderr == b""
    assert rcode == 0


def test_object(tmpdir):
    make_repo(tmpdir)
    with open(join(str(tmpdir), "nodes.py"), 'w') as f:
        f.write("nodes = {'node1': {'metadata': {'foo': object}}}")
    stdout, stderr, rcode = run("bw metadata node1", path=str(tmpdir))
    assert rcode == 1


def test_merge(tmpdir):
    make_repo(
        tmpdir,
        nodes={
            "node1": {
                'groups': {"group1"},
                'metadata': {
                    "foo": {
                        "bar": "baz",
                    },
                },
            },
        },
        groups={
            "group1": {
                'metadata': {
                    "ding": 5,
                    "foo": {
                        "bar": "ZAB",
                        "baz": "bar",
                    },
                },
            },
        },
    )
    stdout, stderr, rcode = run("bw metadata node1", path=str(tmpdir))
    assert loads(stdout.decode()) == {
        "ding": 5,
        "foo": {
            "bar": "baz",
            "baz": "bar",
        },
    }
    assert stderr == b""
    assert rcode == 0


def test_metadatapy(tmpdir):
    make_repo(
        tmpdir,
        bundles={"test": {}},
        nodes={
            "node1": {
                'bundles': ["test"],
                'metadata': {
                    "foo": {
                        "bar": "shizzle",
                    },
                },
            },
        },
    )
    with open(join(str(tmpdir), "bundles", "test", "metadata.py"), 'w') as f:
        f.write(
"""@metadata_reactor
def foo(metadata):
    return {
        "baz": node.name,
        "frob": metadata.get("foo/bar", "shnozzle") + "ay",
        "gob": metadata.get("shlop", "mop"),
    }
""")
    stdout, stderr, rcode = run("bw metadata node1", path=str(tmpdir))
    assert loads(stdout.decode()) == {
        "baz": "node1",
        "foo": {
            "bar": "shizzle",
        },
        "frob": "shizzleay",
        "gob": "mop",
    }
    assert stderr == b""
    assert rcode == 0


def test_metadatapy_defaults(tmpdir):
    make_repo(
        tmpdir,
        bundles={"test": {}},
        nodes={
            "node1": {
                'bundles': ["test"],
                'metadata': {"foo": "bar"},
            },
        },
    )
    with open(join(str(tmpdir), "bundles", "test", "metadata.py"), 'w') as f:
        f.write(
"""defaults = {
    "baz": node.name,
    "foo": "baz",
}
""")
    stdout, stderr, rcode = run("bw metadata node1", path=str(tmpdir))
    assert loads(stdout.decode()) == {
        "baz": "node1",
        "foo": "bar",
    }
    assert stderr == b""
    assert rcode == 0


def test_metadatapy_defaults_atomic(tmpdir):
    make_repo(
        tmpdir,
        bundles={"test": {}},
    )
    with open(join(str(tmpdir), "nodes.py"), 'w') as f:
        f.write(
"""
from bundlewrap.metadata import atomic

nodes = {
    "node1": {
        'bundles': ["test"],
        'metadata': {"foo": atomic({"bar": "baz"})},
    },
}
""")
    with open(join(str(tmpdir), "bundles", "test", "metadata.py"), 'w') as f:
        f.write(
"""defaults = {
    "foo": {
        "bar": "frob",
        "baz": "gobble",
    },
}
""")
    stdout, stderr, rcode = run("bw metadata node1", path=str(tmpdir))
    assert loads(stdout.decode()) == {
        "foo": {"bar": "baz"},
    }
    assert stderr == b""
    assert rcode == 0


def test_metadatapy_update(tmpdir):
    make_repo(
        tmpdir,
        bundles={"test": {}},
        nodes={
            "node1": {
                'bundles': ["test"],
                'metadata': {"foo": "bar"},
            },
        },
    )
    with open(join(str(tmpdir), "bundles", "test", "metadata.py"), 'w') as f:
        f.write(
"""@metadata_reactor
def foo(metadata):
    return {
        "baz": "foo",
        "foo": "baz",
    }
""")
    stdout, stderr, rcode = run("bw metadata node1", path=str(tmpdir))
    assert loads(stdout.decode()) == {
        "baz": "foo",
        "foo": "bar",
    }
    assert stderr == b""
    assert rcode == 0


def test_table(tmpdir):
    make_repo(
        tmpdir,
        nodes={
            "node1": {
                'metadata': {
                    "foo_dict": {
                        "bar": "baz",
                    },
                    "foo_list": ["bar", 1],
                    "foo_int": 47,
                    "foo_umlaut": "föö",
                },
            },
            "node2": {
                'metadata': {
                    "foo_dict": {
                        "baz": "bar",
                    },
                    "foo_list": [],
                    "foo_int": -3,
                    "foo_umlaut": "füü",
                },
            },
        },
        groups={"all": {'member_patterns': {r".*"}}},
    )
    stdout, stderr, rcode = run("BW_TABLE_STYLE=grep bw metadata all -k foo_dict/bar foo_list foo_int foo_umlaut", path=str(tmpdir))
    assert stdout.decode('utf-8') == """node\tfoo_dict/bar\tfoo_int\tfoo_list\tfoo_umlaut
node1\tbaz\t47\tbar, 1\tföö
node2\t<missing>\t-3\t\tfüü
"""
    assert stderr == b""
    assert rcode == 0


def test_metadatapy_merge_order(tmpdir):
    make_repo(
        tmpdir,
        bundles={"test": {}},
        nodes={
            "node1": {
                'bundles': ["test"],
                'groups': {"group1"},
                'metadata': {
                    "four": "node",
                },
            },
        },
        groups={
            "group1": {
                'metadata': {
                    "three": "group",
                    "four": "group",
                },
            },
        },
    )
    with open(join(str(tmpdir), "bundles", "test", "metadata.py"), 'w') as f:
        f.write(
"""defaults = {
    "one": "defaults",
    "two": "defaults",
    "three": "defaults",
    "four": "defaults",
}

@metadata_reactor
def foo_reactor(metadata):
    return {
        "two": "reactor",
        "three": "reactor",
        "four": "reactor",
    }
""")
    stdout, stderr, rcode = run("bw metadata node1", path=str(tmpdir))
    assert loads(stdout.decode()) == {
        "one": "defaults",
        "two": "reactor",
        "three": "group",
        "four": "node",
    }
    assert stderr == b""
    assert rcode == 0


def test_metadatapy_static_reorder(tmpdir):
    make_repo(
        tmpdir,
        bundles={"test": {}},
        nodes={
            "node1": {
                'bundles': ["test"],
                'metadata': {
                    "foo": "bar",
                    "frob": "flup",
                },
            },
        },
    )
    with open(join(str(tmpdir), "bundles", "test", "metadata.py"), 'w') as f:
        f.write(
"""@metadata_reactor
def foo_reactor(metadata):
    return {
        "foo": "overwritten",
        "baz": metadata.get("frob"),
    }
""")
    stdout, stderr, rcode = run("bw metadata node1", path=str(tmpdir))
    assert loads(stdout.decode()) == {
        "foo": "bar",
        "frob": "flup",
        "baz": "flup",
    }
    assert stderr == b""
    assert rcode == 0


def test_metadatapy_reactor_keyerror_from_metastack(tmpdir):
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
@metadata_reactor
def foo_reactor(metadata):
    return {'foo': metadata.get('bar')}
""")
    stdout, stderr, rcode = run("bw metadata node1", path=str(tmpdir))
    assert rcode == 1
    assert b"node1" in stderr
    assert b"foo_reactor" in stderr
    assert b"'bar'" in stderr


def test_metadatapy_reactor_keyerror_from_dict(tmpdir):
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
@metadata_reactor
def foo_reactor(metadata):
    x = {}['baz']
    return {'x': x}
""")
    stdout, stderr, rcode = run("bw metadata node1", path=str(tmpdir))
    assert rcode == 1
    assert b"node1" in stderr
    assert b"foo_reactor" in stderr
    assert b"'baz'" in stderr


def test_metadatapy_reactor_keyerror_fixed(tmpdir):
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
@metadata_reactor
def one(metadata):
    return {'one': True}

@metadata_reactor
def two(metadata):
    return {'two': metadata.get('one')}

@metadata_reactor
def three(metadata):
    return {'three': metadata.get('two')}

@metadata_reactor
def four(metadata):
    return {'four': metadata.get('three')}
""")
    stdout, stderr, rcode = run("bw metadata node1", path=str(tmpdir))
    assert loads(stdout.decode()) == {
        "one": True,
        "two": True,
        "three": True,
        "four": True,
    }
    assert stderr == b""
    assert rcode == 0


def test_metadatapy_infinite_loop(tmpdir):
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
@metadata_reactor
def plusone(metadata):
    return {'foo': metadata.get('bar', 0) + 1 }

@metadata_reactor
def plustwo(metadata):
    return {'bar': metadata.get('foo', 0) + 2 }
""")
    stdout, stderr, rcode = run("bw metadata node1", path=str(tmpdir))
    assert rcode == 1


def test_metadatapy_no_self_react(tmpdir):
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
@metadata_reactor
def reactor1(metadata):
    assert not metadata.get('broken', False)
    return {'broken': True}

@metadata_reactor
def reactor2(metadata):
    # just to make sure reactor1 runs again
    return {'again': True}
""")
    stdout, stderr, rcode = run("bw metadata node1", path=str(tmpdir))
    assert loads(stdout.decode()) == {
        "broken": True,
        "again": True,
    }


def test_own_node_metadata(tmpdir):
    make_repo(
        tmpdir,
        bundles={"test": {}},
        nodes={
            "node1": {
                'bundles': ["test"],
                'metadata': {'number': 47},
            },
        },
    )
    with open(join(str(tmpdir), "bundles", "test", "metadata.py"), 'w') as f:
        f.write(
"""
@metadata_reactor
def reactor1(metadata):
    return {'plusone': node.metadata.get('number') + 1}
""")
    stdout, stderr, rcode = run("bw metadata node1", path=str(tmpdir))
    assert loads(stdout.decode()) == {
        "number": 47,
        "plusone": 48,
    }


def test_other_node_metadata(tmpdir):
    make_repo(
        tmpdir,
        bundles={"test": {}},
        nodes={
            "node1": {
                'bundles': ["test"],
                'metadata': {'number': 47},
            },
            "node2": {
                'bundles': ["test"],
                'metadata': {'number': 42},
            },
            "node3": {
                'bundles': ["test"],
                'metadata': {'number': 23},
            },
        },
    )
    with open(join(str(tmpdir), "bundles", "test", "metadata.py"), 'w') as f:
        f.write(
"""
@metadata_reactor
def reactor1(metadata):
    numbers = set()
    for n in repo.nodes:
        if n != node:
            numbers.add(n.metadata.get('number'))
    return {'other_numbers': numbers}
""")
    stdout, stderr, rcode = run("bw metadata node1", path=str(tmpdir))
    assert loads(stdout.decode()) == {
        "number": 47,
        "other_numbers": [23, 42],
    }
    stdout, stderr, rcode = run("bw metadata node2", path=str(tmpdir))
    assert loads(stdout.decode()) == {
        "number": 42,
        "other_numbers": [23, 47],
    }
    stdout, stderr, rcode = run("bw metadata node3", path=str(tmpdir))
    assert loads(stdout.decode()) == {
        "number": 23,
        "other_numbers": [42, 47],
    }


def test_reactor_provides_not_run(tmpdir):
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
    return {'foo': 1}

@metadata_reactor.provides('bar')
def reactor2(metadata):
    assert False
""")
    stdout, stderr, rcode = run("bw metadata node1", path=str(tmpdir))
    assert rcode == 1
    assert "AssertionError" in stderr.decode()

    stdout, stderr, rcode = run("bw metadata node1 -k foo", path=str(tmpdir))
    assert rcode == 0
    assert loads(stdout.decode()) == {
        'foo': 1,
    }


def test_reactor_provides_chain(tmpdir):
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
    return {
        'foo': {
            'baz': metadata.get('bar'),
        },
    }

@metadata_reactor.provides('bar')
def reactor2(metadata):
    return {'bar': 2}

@metadata_reactor.provides('something irrelevant')
def reactor3(metadata):
    assert False

@metadata_reactor
def reactor4(metadata):
    return {}
""")
    stdout, stderr, rcode = run("bw metadata node1", path=str(tmpdir))
    assert rcode == 1
    assert "AssertionError" in stderr.decode()

    stdout, stderr, rcode = run("bw metadata node1 -k foo", path=str(tmpdir))
    assert rcode == 0
    assert loads(stdout.decode()) == {
        'foo': {
            'baz': 2,
        },
    }
