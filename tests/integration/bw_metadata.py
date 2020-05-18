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
                'metadata': {
                    "foo": {
                        "bar": "baz",
                    },
                },
            },
        },
        groups={
            "group1": {
                'members': ["node1"],
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
        groups={
            "all": {
                'members': ["node1", "node2"],
            },
        },
    )
    stdout, stderr, rcode = run("BW_TABLE_STYLE=grep bw metadata --table all foo_dict bar, foo_list, foo_int, foo_umlaut", path=str(tmpdir))
    assert stdout.decode('utf-8') == """node\tfoo_dict bar\tfoo_list\tfoo_int\tfoo_umlaut
node1\tbaz\tbar, 1\t47\tföö
node2\t<missing>\t\t-3\tfüü
"""
    assert stderr == b""
    assert rcode == 0


def test_table_no_key(tmpdir):
    make_repo(
        tmpdir,
        nodes={
            "node1": {},
        },
    )
    stdout, stderr, rcode = run("bw metadata --table node1", path=str(tmpdir))
    assert rcode == 1


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


def test_metadatapy_do_not_run_me_again(tmpdir):
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
"""called = False
@metadata_reactor
def foo_reactor(metadata):
    global called
    if not called:
        called = True
        raise DoNotRunAgain
    else:
        raise AssertionError


@metadata_reactor
def bar_reactor(metadata):
    return {'called': called}
""")
    stdout, stderr, rcode = run("bw metadata node1", path=str(tmpdir))
    assert loads(stdout.decode()) == {
        "called": True,
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
def foo(metadata):
    bar_ran = metadata.get('bar_ran', False)
    if not bar_ran:
        return {'foo_ran': True}
    else:
        return {'foo': metadata.get('bar'), 'foo_ran': True}


@metadata_reactor
def bar(metadata):
    foo_ran = metadata.get('foo_ran', False)
    if not foo_ran:
        return {'bar_ran': False}
    else:
        return {'bar': 47, 'bar_ran': True}
""")
    stdout, stderr, rcode = run("bw metadata node1", path=str(tmpdir))
    assert loads(stdout.decode()) == {
        "bar": 47,
        "bar_ran": True,
        "foo": 47,
        "foo_ran": True,
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
    return {'foo': metadata.get('foo', 0) + 1 }

@metadata_reactor
def plustwo(metadata):
    return {'foo': metadata.get('foo', 0) + 2 }
""")
    stdout, stderr, rcode = run("bw metadata node1", path=str(tmpdir))
    assert rcode == 1
