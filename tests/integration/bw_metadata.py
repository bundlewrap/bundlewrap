# -*- coding: utf-8 -*-
from __future__ import unicode_literals

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
                'metadata': {"foo": "bar"},
            },
        },
    )
    with open(join(str(tmpdir), "bundles", "test", "metadata.py"), 'w') as f:
        f.write(
"""@metadata_processor
def foo(metadata):
    metadata["baz"] = node.name
    return metadata, DONE
""")
    stdout, stderr, rcode = run("bw metadata node1", path=str(tmpdir))
    assert loads(stdout.decode()) == {
        "baz": "node1",
        "foo": "bar",
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
"""@metadata_processor
def foo(metadata):
    return {
        "foo": "baz",
        "baz": "foo",
    }, DONE, DEFAULTS
""")
    stdout, stderr, rcode = run("bw metadata node1", path=str(tmpdir))
    assert loads(stdout.decode()) == {
        "baz": "foo",
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
"""@metadata_processor
def foo(metadata):
    return {
        "foo": {
            "bar": "frob",
            "baz": "gobble",
        },
    }, DONE, DEFAULTS
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
"""@metadata_processor
def foo(metadata):
    return {
        "foo": "baz",
        "baz": "foo",
    }, DONE, OVERWRITE
""")
    stdout, stderr, rcode = run("bw metadata node1", path=str(tmpdir))
    assert loads(stdout.decode()) == {
        "baz": "foo",
        "foo": "baz",
    }
    assert stderr == b""
    assert rcode == 0


def test_metadatapy_invalid_number_of_elements(tmpdir):
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
"""@metadata_processor
def foo(metadata):
    return metadata
""")
    stdout, stderr, rcode = run("bw metadata node1", path=str(tmpdir))
    assert rcode != 0


def test_metadatapy_invalid_first_element_not_dict(tmpdir):
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
"""@metadata_processor
def foo(metadata):
    return DONE, metadata
""")
    stdout, stderr, rcode = run("bw metadata node1", path=str(tmpdir))
    assert rcode != 0


def test_metadatapy_invalid_defaults_plus_original_dict(tmpdir):
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
"""@metadata_processor
def foo(metadata):
    return metadata, DONE, DEFAULTS
""")
    stdout, stderr, rcode = run("bw metadata node1", path=str(tmpdir))
    assert rcode != 0


def test_metadatapy_invalid_overwrite_plus_original_dict(tmpdir):
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
"""@metadata_processor
def foo(metadata):
    return metadata, DONE, OVERWRITE
""")
    stdout, stderr, rcode = run("bw metadata node1", path=str(tmpdir))
    assert rcode != 0


def test_metadatapy_invalid_option(tmpdir):
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
"""@metadata_processor
def foo(metadata):
    return metadata, DONE, 1000
""")
    stdout, stderr, rcode = run("bw metadata node1", path=str(tmpdir))
    assert rcode != 0


def test_metadatapy_invalid_done_and_again(tmpdir):
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
"""@metadata_processor
def foo(metadata):
    return metadata, DONE, RUN_ME_AGAIN
""")
    stdout, stderr, rcode = run("bw metadata node1", path=str(tmpdir))
    assert rcode != 0


def test_metadatapy_invalid_no_done_or_again(tmpdir):
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
"""@metadata_processor
def foo(metadata):
    return {}, DEFAULTS
""")
    stdout, stderr, rcode = run("bw metadata node1", path=str(tmpdir))
    assert rcode != 0


def test_metadatapy_invalid_defaults_and_overwrite(tmpdir):
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
"""@metadata_processor
def foo(metadata):
    return {}, DEFAULTS, OVERWRITE, DONE
""")
    stdout, stderr, rcode = run("bw metadata node1", path=str(tmpdir))
    assert rcode != 0


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
