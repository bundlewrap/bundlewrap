from os.path import join

from bundlewrap.metadata import atomic, dictionary_key_map
from bundlewrap.utils.testing import make_repo, run


def test_empty(tmpdir):
    make_repo(tmpdir)
    stdout, stderr, rcode = run("bw test", path=str(tmpdir))
    assert stdout == b""


def test_bundle_not_found(tmpdir):
    make_repo(
        tmpdir,
        nodes={
            "node1": {
                'bundles': ["bundle1"],
            },
        },
    )
    assert run("bw test", path=str(tmpdir))[2] == 1


def test_hooks(tmpdir):
    make_repo(
        tmpdir,
        nodes={
            "node1": {},
            "node2": {},
        },
    )
    with open(join(str(tmpdir), "hooks", "test.py"), 'w') as f:
        f.write("""from bundlewrap.utils.ui import io
def test(repo, **kwargs):
    io.stdout("AAA")

def test_node(repo, node, **kwargs):
    io.stdout("BBB")
""")
    assert b"AAA" in run("bw test", path=str(tmpdir))[0]
    assert b"BBB" in run("bw test", path=str(tmpdir))[0]


def test_circular_dep_direct(tmpdir):
    make_repo(
        tmpdir,
        nodes={
            "node1": {
                'bundles': ["bundle1"],
            },
        },
        bundles={
            "bundle1": {
                "pkg_apt": {
                    "foo": {
                        'needs': ["pkg_apt:bar"],
                    },
                    "bar": {
                        'needs': ["pkg_apt:foo"],
                    },
                },
            },
        },
    )
    assert run("bw test", path=str(tmpdir))[2] == 1


def test_circular_dep_indirect(tmpdir):
    make_repo(
        tmpdir,
        nodes={
            "node1": {
                'bundles': ["bundle1"],
            },
        },
        bundles={
            "bundle1": {
                "pkg_apt": {
                    "foo": {
                        'needs': ["pkg_apt:bar"],
                    },
                    "bar": {
                        'needs': ["pkg_apt:baz"],
                    },
                    "baz": {
                        'needs': ["pkg_apt:foo"],
                    },
                },
            },
        },
    )
    assert run("bw test", path=str(tmpdir))[2] == 1


def test_circular_dep_self(tmpdir):
    make_repo(
        tmpdir,
        nodes={
            "node1": {
                'bundles': ["bundle1"],
            },
        },
        bundles={
            "bundle1": {
                "pkg_apt": {
                    "foo": {
                        'needs': ["pkg_apt:foo"],
                    },
                },
            },
        },
    )
    assert run("bw test", path=str(tmpdir))[2] == 1


def test_circular_trigger_self(tmpdir):
    make_repo(
        tmpdir,
        nodes={
            "node1": {
                'bundles': ["bundle1"],
            },
        },
        bundles={
            "bundle1": {
                "pkg_apt": {
                    "foo": {
                        'triggers': ["pkg_apt:foo"],
                    },
                },
            },
        },
    )
    assert run("bw test", path=str(tmpdir))[2] == 1


def test_file_invalid_attribute(tmpdir):
    make_repo(
        tmpdir,
        nodes={
            "node1": {
                'bundles': ["bundle1"],
            },
        },
        bundles={
            "bundle1": {
                "files": {
                    "/foo": {
                        "potato": "yes",
                    },
                },
            },
        },
    )
    assert run("bw test", path=str(tmpdir))[2] == 1


def test_file_template_error(tmpdir):
    make_repo(
        tmpdir,
        nodes={
            "node1": {
                'bundles': ["bundle1"],
            },
        },
        bundles={
            "bundle1": {
                "files": {
                    "/foo": {
                        'content_type': 'mako',
                        'content': "${broken",
                    },
                },
            },
        },
    )
    assert run("bw test", path=str(tmpdir))[2] == 1


def test_group_loop(tmpdir):
    make_repo(
        tmpdir,
        groups={
            "group1": {
                'subgroups': ["group2"],
            },
            "group2": {
                'subgroups': ["group3"],
            },
            "group3": {
                'subgroups': ["group1"],
            },
        },
    )
    assert run("bw test", path=str(tmpdir))[2] == 1


def test_dictmap():
    assert set(dictionary_key_map({
        'key1': 1,
        'key2': {
            'key3': [3, 3, 3],
            'key4': atomic([4, 4, 4]),
            'key5': {
                'key6': "6",
            },
            'key7': set((7, 7, 7)),
        },
    })) == set([
        ("key1",),
        ("key2",),
        ("key2", "key3"),
        ("key2", "key4"),
        ("key2", "key5"),
        ("key2", "key5", "key6"),
        ("key2", "key7"),
    ])


def test_group_metadata_collision(tmpdir):
    make_repo(
        tmpdir,
        nodes={"node1": {}},
        groups={
            "group1": {
                'members': ["node1"],
                'metadata': {
                    'foo': {
                        'baz': 1,
                    },
                    'bar': 2,
                },
            },
            "group2": {
                'metadata': {
                    'foo': {
                        'baz': 3,
                    },
                    'snap': 4,
                },
                'subgroups': ["group3"],
            },
            "group3": {
                'members': ["node1"],
            },
        },
    )
    assert run("bw test", path=str(tmpdir))[2] == 1


def test_group_metadata_collision_subgroups(tmpdir):
    make_repo(
        tmpdir,
        nodes={"node1": {}},
        groups={
            "group1": {
                'members': ["node1"],
                'metadata': {
                    'foo': {
                        'baz': 1,
                    },
                    'bar': 2,
                },
            },
            "group2": {
                'metadata': {
                    'foo': {
                        'baz': 3,
                    },
                    'snap': 4,
                },
                'subgroups': ["group1", "group3"],
            },
            "group3": {
                'members': ["node1"],
            },
        },
    )
    assert run("bw test", path=str(tmpdir))[2] == 0


def test_group_metadata_collision_list(tmpdir):
    make_repo(
        tmpdir,
        nodes={"node1": {}},
        groups={
            "group1": {
                'members': ["node1"],
                'metadata': {
                    'foo': [1],
                },
            },
            "group2": {
                'members': ["node1"],
                'metadata': {
                    'foo': [2],
                },
            },
        },
    )
    assert run("bw test", path=str(tmpdir))[2] == 1


def test_group_metadata_collision_dict(tmpdir):
    make_repo(
        tmpdir,
        nodes={"node1": {}},
        groups={
            "group1": {
                'members': ["node1"],
                'metadata': {
                    'foo': {'bar': 1},
                },
            },
            "group2": {
                'members': ["node1"],
                'metadata': {
                    'foo': 2,
                },
            },
        },
    )
    assert run("bw test", path=str(tmpdir))[2] == 1


def test_group_metadata_collision_dict_ok(tmpdir):
    make_repo(
        tmpdir,
        nodes={"node1": {}},
        groups={
            "group1": {
                'members': ["node1"],
                'metadata': {
                    'foo': {'bar': 1},
                },
            },
            "group2": {
                'members': ["node1"],
                'metadata': {
                    'foo': {'baz': 2},
                },
            },
        },
    )
    assert run("bw test", path=str(tmpdir))[2] == 0


def test_group_metadata_collision_set(tmpdir):
    make_repo(
        tmpdir,
        nodes={"node1": {}},
        groups={
            "group1": {
                'members': ["node1"],
                'metadata': {
                    'foo': set([1]),
                },
            },
            "group2": {
                'members': ["node1"],
                'metadata': {
                    'foo': 2,
                },
            },
        },
    )
    assert run("bw test", path=str(tmpdir))[2] == 1


def test_group_metadata_collision_set_ok(tmpdir):
    make_repo(
        tmpdir,
        nodes={"node1": {}},
        groups={
            "group1": {
                'members': ["node1"],
                'metadata': {
                    'foo': set([1]),
                },
            },
            "group2": {
                'members': ["node1"],
                'metadata': {
                    'foo': set([2]),
                },
            },
        },
    )
    assert run("bw test", path=str(tmpdir))[2] == 0
