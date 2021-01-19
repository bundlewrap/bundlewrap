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
                'items': {
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
                'items': {
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
                'items': {
                    "pkg_apt": {
                        "foo": {
                            'needs': ["pkg_apt:foo"],
                        },
                    },
                },
            },
        },
    )
    assert run("bw test -I", path=str(tmpdir))[2] == 1


def test_unknown_tag(tmpdir):
    make_repo(
        tmpdir,
        nodes={
            "node1": {
                'bundles': ["bundle1"],
            },
        },
        bundles={
            "bundle1": {
                'items': {
                    "files": {
                        "/foo": {
                            'content': "none",
                            'needs': {
                                "tag:bar",
                            },
                        },
                    },
                },
            },
        },
    )
    assert run("bw test -I", path=str(tmpdir))[2] == 0


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
                'items': {
                    "pkg_apt": {
                        "foo": {
                            'triggers': ["pkg_apt:foo"],
                        },
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
                'items': {
                    "files": {
                        "/foo": {
                            "potato": "yes",
                        },
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
                'items': {
                    "files": {
                        "/foo": {
                            'content_type': 'mako',
                            'content': "${broken",
                        },
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
        nodes={
            "node1": {
                'groups': {
                    "group1",
                    "group3",
                },
            },
        },
        groups={
            "group1": {
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
            "group3": {},
        },
    )
    assert run("bw test -M", path=str(tmpdir))[2] == 1


def test_group_metadata_collision_subgroups(tmpdir):
    make_repo(
        tmpdir,
        nodes={
            "node1": {
                'groups': {
                    "group1",
                    "group3",
                },
            },
        },
        groups={
            "group1": {
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
            "group3": {},
        },
    )
    assert run("bw test -M", path=str(tmpdir))[2] == 0


def test_group_metadata_collision_list(tmpdir):
    make_repo(
        tmpdir,
        nodes={
            "node1": {
                'groups': {
                    "group1",
                    "group2",
                },
            },
        },
        groups={
            "group1": {
                'metadata': {
                    'foo': [1],
                },
            },
            "group2": {
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
        nodes={
            "node1": {
                'groups': {
                    "group1",
                    "group2",
                },
            },
        },
        groups={
            "group1": {
                'metadata': {
                    'foo': {'bar': 1},
                },
            },
            "group2": {
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
        nodes={
            "node1": {
                'groups': {
                    "group1",
                    "group2",
                },
            },
        },
        groups={
            "group1": {
                'metadata': {
                    'foo': {'bar': 1},
                },
            },
            "group2": {
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
        nodes={
            "node1": {
                'groups': {
                    "group1",
                    "group2",
                },
            },
        },
        groups={
            "group1": {
                'metadata': {
                    'foo': set([1]),
                },
            },
            "group2": {
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
        nodes={
            "node1": {
                'groups': {
                    "group1",
                    "group2",
                },
            },
        },
        groups={
            "group1": {
                'metadata': {
                    'foo': set([1]),
                },
            },
            "group2": {
                'metadata': {
                    'foo': set([2]),
                },
            },
        },
    )
    assert run("bw test -M", path=str(tmpdir))[2] == 0


def test_defaults_metadata_collision(tmpdir):
    make_repo(
        tmpdir,
        nodes={
            "node1": {
                'bundles': {"bundle1", "bundle2"},
            },
        },
        bundles={
            "bundle1": {},
            "bundle2": {},
        },
    )
    with open(join(str(tmpdir), "bundles", "bundle1", "metadata.py"), 'w') as f:
        f.write(
"""defaults = {
    "foo": "bar",
}
""")
    with open(join(str(tmpdir), "bundles", "bundle2", "metadata.py"), 'w') as f:
        f.write(
"""defaults = {
    "foo": "baz",
}
""")
    stdout, stderr, rcode = run("bw test -M", path=str(tmpdir))
    assert rcode == 1
    assert b"foo" in stderr


def test_defaults_metadata_collision_nested(tmpdir):
    make_repo(
        tmpdir,
        nodes={
            "node1": {
                'bundles': {"bundle1", "bundle2"},
            },
        },
        bundles={
            "bundle1": {},
            "bundle2": {},
        },
    )
    with open(join(str(tmpdir), "bundles", "bundle1", "metadata.py"), 'w') as f:
        f.write(
"""defaults = {
    "foo": {"bar": "baz"},
}
""")
    with open(join(str(tmpdir), "bundles", "bundle2", "metadata.py"), 'w') as f:
        f.write(
"""defaults = {
    "foo": {"bar": "frob"},
}
""")
    stdout, stderr, rcode = run("bw test -M", path=str(tmpdir))
    assert rcode == 1
    assert b"foo/bar" in stderr


def test_defaults_metadata_collision_ok(tmpdir):
    make_repo(
        tmpdir,
        nodes={
            "node1": {
                'bundles': {"bundle1", "bundle2"},
            },
        },
        bundles={
            "bundle1": {},
            "bundle2": {},
        },
    )
    with open(join(str(tmpdir), "bundles", "bundle1", "metadata.py"), 'w') as f:
        f.write(
"""defaults = {
    "foo": {"bar"},
}
""")
    with open(join(str(tmpdir), "bundles", "bundle2", "metadata.py"), 'w') as f:
        f.write(
"""defaults = {
    "foo": {"baz"},
}
""")
    assert run("bw test -M", path=str(tmpdir))[2] == 0


def test_reactor_metadata_collision(tmpdir):
    make_repo(
        tmpdir,
        nodes={
            "node1": {
                'bundles': {"bundle1", "bundle2"},
            },
        },
        bundles={
            "bundle1": {},
            "bundle2": {},
        },
    )
    with open(join(str(tmpdir), "bundles", "bundle1", "metadata.py"), 'w') as f:
        f.write(
"""@metadata_reactor
def foo(metadata):
    return {"foo": 1}
""")
    with open(join(str(tmpdir), "bundles", "bundle2", "metadata.py"), 'w') as f:
        f.write(
"""@metadata_reactor
def foo(metadata):
    return {"foo": 2}
""")
    stdout, stderr, rcode = run("bw test -M", path=str(tmpdir))
    assert rcode == 1
    assert b"foo" in stderr


def test_reactor_metadata_collision_nested(tmpdir):
    make_repo(
        tmpdir,
        nodes={
            "node1": {
                'bundles': {"bundle1", "bundle2"},
            },
        },
        bundles={
            "bundle1": {},
            "bundle2": {},
        },
    )
    with open(join(str(tmpdir), "bundles", "bundle1", "metadata.py"), 'w') as f:
        f.write(
"""@metadata_reactor
def foo(metadata):
    return {"foo": {"bar": "1"}}
""")
    with open(join(str(tmpdir), "bundles", "bundle2", "metadata.py"), 'w') as f:
        f.write(
"""@metadata_reactor
def foo(metadata):
    return {"foo": {"bar": "2"}}
""")
    stdout, stderr, rcode = run("bw test -M", path=str(tmpdir))
    assert rcode == 1
    assert b"foo/bar" in stderr


def test_reactor_metadata_collision_nested_mixed(tmpdir):
    make_repo(
        tmpdir,
        nodes={
            "node1": {
                'bundles': {"bundle1", "bundle2"},
            },
        },
        bundles={
            "bundle1": {},
            "bundle2": {},
        },
    )
    with open(join(str(tmpdir), "bundles", "bundle1", "metadata.py"), 'w') as f:
        f.write(
"""@metadata_reactor
def foo(metadata):
    return {"foo": {"bar": {True}}}
""")
    with open(join(str(tmpdir), "bundles", "bundle2", "metadata.py"), 'w') as f:
        f.write(
"""@metadata_reactor
def foo(metadata):
    return {"foo": {"bar": [False]}}
""")
    stdout, stderr, rcode = run("bw test -M", path=str(tmpdir))
    assert rcode == 1
    assert b"foo/bar" in stderr


def test_reactor_provides_ok(tmpdir):
    make_repo(
        tmpdir,
        nodes={
            "node1": {
                'bundles': {"bundle1"},
            },
        },
        bundles={
            "bundle1": {},
        },
    )
    with open(join(str(tmpdir), "bundles", "bundle1", "metadata.py"), 'w') as f:
        f.write(
"""@metadata_reactor.provides("foo")
def foo(metadata):
    return {"foo": 1}
""")
    stdout, stderr, rcode = run("bw test -p", path=str(tmpdir))
    assert rcode == 0


def test_reactor_provides_violated(tmpdir):
    make_repo(
        tmpdir,
        nodes={
            "node1": {
                'bundles': {"bundle1"},
            },
        },
        bundles={
            "bundle1": {},
        },
    )
    with open(join(str(tmpdir), "bundles", "bundle1", "metadata.py"), 'w') as f:
        f.write(
"""@metadata_reactor.provides("foo")
def foo(metadata):
    return {"bar": 1}
""")
    stdout, stderr, rcode = run("bw test -p", path=str(tmpdir))
    assert rcode == 1
    assert "foo" in stderr.decode()
    assert "bar" in stderr.decode()


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
                'items': {
                    "files": {
                        "/foo": {
                            'content_type': 'mako',
                            'content': "${repo.vault.decrypt('bzzt', key='unavailable')}",
                        },
                    },
                },
            },
        },
    )
    assert run("bw test -I", path=str(tmpdir))[2] == 1
    assert run("bw test -iI", path=str(tmpdir))[2] == 0


def test_fault_missing_content(tmpdir):
    make_repo(
        tmpdir,
        nodes={
            "node1": {
                'bundles': ["bundle1"],
            },
        },
        bundles={
            "bundle1": {}
        },
    )
    with open(join(str(tmpdir), "bundles", "bundle1", "items.py"), 'w') as f:
        f.write("""
files = {
    "/foo": {
        'content': repo.vault.decrypt("bzzt", key="unavailable"),
    },
}
""")
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
        f.write("""@metadata_reactor
def test(metadata):
    return {'test': 1}
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
n = randint(1, 99999)

@metadata_reactor
def test(metadata):
    return {'findme': n}
""")
    stdout, stderr, rcode = run("bw test -m 3", path=str(tmpdir))
    assert rcode == 1
    assert b"findme" in stderr


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
                'items': {
                    "files": {
                        "/test": {
                            'content': "1",
                            'content_type': 'mako',
                        },
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
                'items': {
                    "files": {
                        "/test": {
                            'content': "<% from random import randint %>\n${randint(1, 99999)\n}",
                            'content_type': 'mako',
                        },
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
            "node1": {'groups': {"group2"}},
        },
        groups={
            "group1": {'subgroups': ["missing-group"]},
            "group2": {},
        },
    )
    assert run("bw test", path=str(tmpdir))[2] == 1
    assert run("bw test group1", path=str(tmpdir))[2] == 1
    assert run("bw test group2", path=str(tmpdir))[2] == 1


def test_empty_group(tmpdir):
    make_repo(
        tmpdir,
        nodes={
            "node1": {'groups': {"group2"}},
        },
        groups={
            "group1": {},
            "group2": {},
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
                'items': {
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
                'items': {
                    "users": {
                        "user1": {},
                    },
                    "groups": {
                        "group1": {'delete': True},
                    },
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
                'items': {
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
        },
    )
    assert run("bw test -I", path=str(tmpdir))[2] == 1


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
                'items': {
                    'files': {
                        "/test": {
                            'content': "test",
                        },
                    },
                },
            },
            "bundle2": {
                'items': {
                    'files': {
                        "/test2": {
                            'content': "test",
                            'needed_by': ["bundle:bundle1"],
                        },
                    },
                },
            },
        },
    )

    stdout, stderr, rcode = run("bw test", path=str(tmpdir))
    assert rcode == 0


def test_bundlepy_tag_loop(tmpdir):
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
                        "a": {
                            'needs': {"tag:b"},
                        },
                        "b": {
                            'needs': {"tag:a"},
                        },
                    },
                },
                'items': {
                    'actions': {
                        "one": {
                            'command': "true",
                            'tags': {"a"},
                        },
                        "two": {
                            'command': "true",
                            'tags': {"b"},
                        },
                    },
                },
            },
        },
    )
    stdout, stderr, rcode = run("bw test -I", path=str(tmpdir))
    assert rcode == 1
    assert "action:one" in stderr.decode()
    assert "action:two" in stderr.decode()


def test_bundlepy_tag_loop2(tmpdir):
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
                        "one": {
                            'needed_by': {"tag:two"},
                        },
                        "two": {
                            'needed_by': {"action:late"},
                        },
                    },
                },
                'items': {
                    'actions': {
                        "early": {
                            'command': "true",
                            'needed_by': {"tag:one"},
                        },
                        "fill_tag_one": {
                            'command': "true",
                            'tags': {"one"},
                        },
                        "fill_tag_two": {
                            'command': "true",
                            'tags': {"two"},
                        },
                        "late": {
                            'command': "true",
                            'needed_by': {"action:early"},  # this makes the loop
                        },
                    },
                },
            },
        },
    )
    stdout, stderr, rcode = run("bw test -I", path=str(tmpdir))
    assert rcode == 1
    assert "action:late" in stderr.decode()
