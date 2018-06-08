from os.path import join

from bundlewrap.utils.testing import make_repo, run


def test_empty(tmpdir):
    make_repo(tmpdir)
    stdout, stderr, rcode = run("bw test", path=str(tmpdir))
    assert stdout == b""
    assert stderr == b""
    assert rcode == 0


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
    assert b"AAA" in run("bw test -H", path=str(tmpdir))[0]
    assert b"BBB" in run("bw test -J", path=str(tmpdir))[0]


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
    assert run("bw test -I", path=str(tmpdir))[2] == 1


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
    assert run("bw test -I", path=str(tmpdir))[2] == 1


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
    assert run("bw test -I", path=str(tmpdir))[2] == 1


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
    assert run("bw test -I", path=str(tmpdir))[2] == 1


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
    assert run("bw test -I", path=str(tmpdir))[2] == 1


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
    assert run("bw test -I", path=str(tmpdir))[2] == 1


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
    assert run("bw test -S", path=str(tmpdir))[2] == 1


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
    assert run("bw test -M", path=str(tmpdir))[2] == 1


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
    assert run("bw test -M", path=str(tmpdir))[2] == 0


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
    assert run("bw test -M", path=str(tmpdir))[2] == 1


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
    assert run("bw test -M", path=str(tmpdir))[2] == 1


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
    assert run("bw test -M", path=str(tmpdir))[2] == 0


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
    assert run("bw test -M", path=str(tmpdir))[2] == 1


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
    assert run("bw test -M", path=str(tmpdir))[2] == 0


def test_fault_missing(tmpdir):
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
                        'content': "${repo.vault.decrypt('bzzt', key='unavailable')}",
                    },
                },
            },
        },
    )
    assert run("bw test -I", path=str(tmpdir))[2] == 1
    assert run("bw test -iI", path=str(tmpdir))[2] == 0


def test_metadata_determinism_ok(tmpdir):
    make_repo(
        tmpdir,
        nodes={
            "node1": {
                'bundles': ["bundle1"],
            },
        },
        bundles={
            "bundle1": {},
        },
    )
    with open(join(str(tmpdir), "bundles", "bundle1", "metadata.py"), 'w') as f:
        f.write("""@metadata_processor
def test(metadata):
    metadata['test'] = 1
    return metadata, DONE
""")
    assert run("bw test -m 3", path=str(tmpdir))[2] == 0


def test_metadata_determinism_broken(tmpdir):
    make_repo(
        tmpdir,
        nodes={
            "node1": {
                'bundles': ["bundle1"],
            },
        },
        bundles={
            "bundle1": {},
        },
    )
    with open(join(str(tmpdir), "bundles", "bundle1", "metadata.py"), 'w') as f:
        f.write("""from random import randint

@metadata_processor
def test(metadata):
    metadata.setdefault('test', randint(1, 99999))
    return metadata, DONE
""")
    assert run("bw test -m 3", path=str(tmpdir))[2] == 1


def test_config_determinism_ok(tmpdir):
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
                    "/test": {
                        'content': "1",
                        'content_type': 'mako',
                    },
                },
            },
        },
    )
    assert run("bw test -d 3", path=str(tmpdir))[2] == 0


def test_config_determinism_broken(tmpdir):
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
                    "/test": {
                        'content': "<% from random import randint %>\n${randint(1, 99999)\n}",
                        'content_type': 'mako',
                    },
                },
            },
        },
    )
    assert run("bw test -d 3", path=str(tmpdir))[2] == 1


def test_unknown_subgroup(tmpdir):
    make_repo(
        tmpdir,
        nodes={
            "node1": {},
        },
        groups={
            "group1": {'subgroups': ["missing-group"]},
            "group2": {'members': ["node1"]},
        },
    )
    assert run("bw test", path=str(tmpdir))[2] == 1
    assert run("bw test group1", path=str(tmpdir))[2] == 1
    assert run("bw test group2", path=str(tmpdir))[2] == 1


def test_empty_group(tmpdir):
    make_repo(
        tmpdir,
        nodes={
            "node1": {},
        },
        groups={
            "group1": {},
            "group2": {'members': ["node1"]},
        },
    )
    assert run("bw test", path=str(tmpdir))[2] == 0
    assert run("bw test -e", path=str(tmpdir))[2] == 1


def test_group_user_dep_deleted(tmpdir):
    make_repo(
        tmpdir,
        nodes={
            "node1": {
                'bundles': ["bundle1"],
            },
        },
        bundles={
            "bundle1": {
                "users": {
                    "user1": {
                        'groups': ["group1"],
                    },
                },
                "groups": {
                    "group1": {
                        'delete': True,
                    },
                },
            },
        },
    )
    assert run("bw test -I", path=str(tmpdir))[2] == 1


def test_group_user_dep_ok(tmpdir):
    # regression test for #341
    make_repo(
        tmpdir,
        nodes={
            "node1": {
                'bundles': ["bundle1"],
            },
        },
        bundles={
            "bundle1": {
                "users": {
                    "user1": {},
                },
                "groups": {
                    "group1": {'delete': True},
                },
            },
        },
    )
    assert run("bw test -I", path=str(tmpdir))[2] == 0


def test_group_user_dep_deleted_gid(tmpdir):
    make_repo(
        tmpdir,
        nodes={
            "node1": {
                'bundles': ["bundle1"],
            },
        },
        bundles={
            "bundle1": {
                "users": {
                    "user1": {
                        'gid': "group1",
                    },
                },
                "groups": {
                    "group1": {
                        'delete': True,
                    },
                },
            },
        },
    )
    assert run("bw test -I", path=str(tmpdir))[2] == 1


def test_secret_identifier_only_once(tmpdir):
    make_repo(
        tmpdir,
        nodes={
            "node1": {
                'bundles': ["bundle1"],
            },
        },
        bundles={
            "bundle1": {
                'files': {
                    "/test": {
                        'content': "${repo.vault.password_for('testing')}",
                        'content_type': 'mako',
                    },
                },
            },
        },
    )
    assert run("bw test -s ''", path=str(tmpdir))[2] == 1
    assert run("bw test -s 'test'", path=str(tmpdir))[2] == 0
    assert run("bw test -s 'test,foo'", path=str(tmpdir))[2] == 0


def test_secret_identifier_twice(tmpdir):
    make_repo(
        tmpdir,
        nodes={
            "node1": {
                'bundles': ["bundle1"],
            },
            "node2": {
                'bundles': ["bundle1"],
            },
        },
        bundles={
            "bundle1": {
                'files': {
                    "/test": {
                        'content': "${repo.vault.password_for('testing')}",
                        'content_type': 'mako',
                    },
                },
            },
        },
    )
    assert run("bw test -s ''", path=str(tmpdir))[2] == 0
    assert run("bw test -s 'test'", path=str(tmpdir))[2] == 0
    assert run("bw test -s 'test,foo'", path=str(tmpdir))[2] == 0


def test_reverse_dummy_dep(tmpdir):
    make_repo(
        tmpdir,
        nodes={
            "node1": {
                'bundles': ["bundle1", "bundle2"],
            },
        },
        bundles={
            "bundle1": {
                'files': {
                    "/test": {
                        'content': "test",
                    },
                },
            },
            "bundle2": {
                'files': {
                    "/test2": {
                        'content': "test",
                        'needed_by': ["bundle:bundle1"],
                    },
                },
            },
        },
    )

    stdout, stderr, rcode = run("bw test", path=str(tmpdir))
    assert rcode == 0
