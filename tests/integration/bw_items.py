from bundlewrap.utils.testing import make_repo, run


def test_file_preview(tmpdir):
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
                    'files': {
                        "/test": {
                            'content': "föö",
                            'encoding': 'latin-1',
                        },
                    },
                },
            },
        },
    )

    stdout, stderr, rcode = run("bw items -f node1 file:/test", path=str(tmpdir))
    assert stdout == "föö".encode('utf-8')  # our output is always utf-8
    assert rcode == 0


def test_multiple_file_preview(tmpdir):
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
                    'files': {
                        "/test": {
                            'content': "föö",
                        },
                        "/testdir/test2": {
                            'content': "bar",
                        },
                    },
                },
            },
        },
    )

    stdout, stderr, rcode = run("bw items -w itemprev node1", path=str(tmpdir))
    assert rcode == 0
    assert tmpdir.join("itemprev/test").exists()
    assert tmpdir.join("itemprev/testdir/test2").exists()


def test_fault_unavailable(tmpdir):
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
                    'files': {
                        "/test": {
                            'content': "${repo.vault.password_for('test', key='404')}",
                            'content_type': 'mako',
                        },
                    },
                },
            },
        },
    )

    stdout, stderr, rcode = run("bw items -f node1 file:/test", path=str(tmpdir))
    assert rcode == 1


def test_fault_unavailable_multiple(tmpdir):
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
                    'files': {
                        "/test": {
                            'content': "föö",
                        },
                        "/testdir/test3": {
                            'content': "${repo.vault.password_for('test', key='404')}",
                            'content_type': 'mako',
                        },
                    },
                },
            },
        },
    )

    stdout, stderr, rcode = run("bw items -w itemprev node1", path=str(tmpdir))
    assert rcode == 0
    assert tmpdir.join("itemprev/test").exists()
    assert not tmpdir.join("itemprev/testdir/test3").exists()


def test_tag_inheritance(tmpdir):
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
                        "directly": {
                            'tags': {"inherited"},
                        },
                    },
                },
                'items': {
                    'actions': {
                        "test": {
                            'command': "true",
                            'tags': {"directly"},
                        },
                    },
                },
            },
        },
    )
    stdout, stderr, rcode = run("bw items --attrs node1 action:test", path=str(tmpdir))
    assert rcode == 0
    assert "inherited" in stdout.decode()


def test_tag_inheritance_loop(tmpdir):
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
                        "directly": {
                            'tags': {"inherited"},
                        },
                        "inherited": {
                            'tags': {"looped"},
                        },
                        "looped": {
                            'tags': {"inherited"},
                            'needs': {"action:dep"},
                        },
                    },
                },
                'items': {
                    'actions': {
                        "test": {
                            'command': "true",
                            'tags': {"directly"},
                        },
                        "dep": {
                            'command': "true",
                        },
                    },
                },
            },
        },
    )
    stdout, stderr, rcode = run("bw items --attrs node1 action:test", path=str(tmpdir))
    assert rcode == 0
    assert "inherited" in stdout.decode()
    assert "looped" in stdout.decode()
    assert "action:dep" in stdout.decode()


def test_duplicate_items(tmpdir):
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
                    'actions': {
                        "dupl": {
                            'command': "true",
                        },
                    },
                },
            },
            "bundle2": {
                'items': {
                    'actions': {
                        "dupl": {
                            'command': "true",
                        },
                    },
                },
            },
        },
    )
    stdout, stderr, rcode = run("bw items node1", path=str(tmpdir))
    assert rcode == 1
    assert "action:dupl" in stderr.decode()
    assert "bundle1" in stderr.decode()
    assert "bundle2" in stderr.decode()


def test_show_auto_needs(tmpdir):
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
                    'directories': {
                        "/foo": {},
                        "/foo/bar": {'needs': {"action:"}},
                    },
                },
            },
        },
    )
    stdout, stderr, rcode = run("BW_TABLE_STYLE=grep bw items --attr node1 directory:/foo/bar needs", path=str(tmpdir))
    assert stdout.decode() == """attribute\tvalue
needs\taction:
needs\tdirectory:/foo
"""
    assert stderr.decode() == ""
    assert rcode == 0


def _test_bw_items_invocation_succeeds(tmpdir, invocation, expected_output):
    stdout, stderr, rcode = run(f"BW_TABLE_STYLE=grep {invocation}", path=str(tmpdir))
    assert stdout.decode() == expected_output
    assert stderr.decode() == ""
    assert rcode == 0


def _bw_items_invocation_make_repo(tmpdir):
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
                    'directories': {
                        "/foo/bar": {'needs': {"action:"}},
                    },
                    'files': {
                        "/foo/bar/moo": {'content': 'bar\n'},
                    },
                    'actions': {
                        "clone_code": {'command': 'git clone'},
                    },
                },
            },
        },
    )


def test_bw_items_invocation_list_of_items(tmpdir):
    _bw_items_invocation_make_repo(tmpdir)
    _test_bw_items_invocation_succeeds(tmpdir, 'bw items node1', """
items
action:clone_code
directory:/foo/bar
file:/foo/bar/moo
""".lstrip())


def test_bw_items_invocation_list_of_items_as_json(tmpdir):
    _bw_items_invocation_make_repo(tmpdir)
    _test_bw_items_invocation_succeeds(tmpdir, 'bw items --json node1', """
[
    "action:clone_code",
    "directory:/foo/bar",
    "file:/foo/bar/moo"
]
""".lstrip())


def test_bw_items_invocation_list_of_items_repr(tmpdir):
    _bw_items_invocation_make_repo(tmpdir)
    _test_bw_items_invocation_succeeds(tmpdir, 'bw items --repr node1', """
items
<Item action:clone_code>
<Directory path:/foo/bar purge:False owner:root group:root mode:0755>
<File path:/foo/bar/moo content_type:text owner:root group:root mode:0644 delete:False>
""".lstrip())


def test_bw_items_invocation_list_of_items_repr_as_json(tmpdir):
    _bw_items_invocation_make_repo(tmpdir)
    _test_bw_items_invocation_succeeds(tmpdir, 'bw items --repr --json node1', """
[
    "<Item action:clone_code>",
    "<Directory path:/foo/bar purge:False owner:root group:root mode:0755>",
    "<File path:/foo/bar/moo content_type:text owner:root group:root mode:0644 delete:False>"
]
""".lstrip())


def test_bw_items_invocation_list_of_items_blame(tmpdir):
    _bw_items_invocation_make_repo(tmpdir)
    _test_bw_items_invocation_succeeds(tmpdir, 'bw items --blame node1', """
bundle name\titems
bundle1\taction:clone_code
bundle1\tdirectory:/foo/bar
bundle1\tfile:/foo/bar/moo
""".lstrip())


def test_bw_items_invocation_list_of_items_blame_as_json(tmpdir):
    _bw_items_invocation_make_repo(tmpdir)
    _test_bw_items_invocation_succeeds(tmpdir, 'bw items --blame --json node1', """
{
    "bundle1": [
        "action:clone_code",
        "directory:/foo/bar",
        "file:/foo/bar/moo"
    ]
}
""".lstrip())


def test_bw_items_invocation_single_item(tmpdir):
    _bw_items_invocation_make_repo(tmpdir)
    _test_bw_items_invocation_succeeds(tmpdir, 'bw items node1 directory:/foo/bar', """
attribute\tvalue
group\troot
mode\t0755
owner\troot
paths_to_purge\t[]
type\tdirectory
""".lstrip())


def test_bw_items_invocation_single_item_as_json(tmpdir):
    _bw_items_invocation_make_repo(tmpdir)
    _test_bw_items_invocation_succeeds(tmpdir, 'bw items --json node1 directory:/foo/bar', """
{
    "group": "root",
    "mode": "0755",
    "owner": "root",
    "paths_to_purge": [],
    "type": "directory"
}
""".lstrip())


def test_bw_items_invocation_single_item_repr(tmpdir):
    _bw_items_invocation_make_repo(tmpdir)
    _test_bw_items_invocation_succeeds(tmpdir, 'bw items --repr node1 directory:/foo/bar', """
item
<Directory path:/foo/bar purge:False owner:root group:root mode:0755>
""".lstrip())


def test_bw_items_invocation_single_item_repr_as_json(tmpdir):
    _bw_items_invocation_make_repo(tmpdir)
    _test_bw_items_invocation_succeeds(tmpdir, 'bw items --repr --json node1 directory:/foo/bar', """
[
    "<Directory path:/foo/bar purge:False owner:root group:root mode:0755>"
]
""".lstrip())


def test_bw_items_invocation_single_item_attrs(tmpdir):
    _bw_items_invocation_make_repo(tmpdir)
    _test_bw_items_invocation_succeeds(tmpdir, 'bw items --attrs node1 directory:/foo/bar', """
attribute\tvalue
after\t[]
before\t[]
canned_actions_inherit_tags	True
cascade_skip\tTrue
comment\tNone
error_on_missing_fault\tFalse
needed_by\t[]
needs\taction:
preceded_by\t[]
precedes\t[]
skip\tFalse
tags\t[]
triggered\tFalse
triggered_by\t[]
triggers\t[]
unless\t
when_creating\t{}
""".lstrip())


def test_bw_items_invocation_single_item_attrs_as_json(tmpdir):
    _bw_items_invocation_make_repo(tmpdir)
    _test_bw_items_invocation_succeeds(tmpdir, 'bw items --attrs --json node1 directory:/foo/bar', """
{
    "after": [],
    "before": [],
    "canned_actions_inherit_tags": true,
    "cascade_skip": true,
    "comment": null,
    "error_on_missing_fault": false,
    "needed_by": [],
    "needs": [
        "action:"
    ],
    "preceded_by": [],
    "precedes": [],
    "skip": false,
    "tags": [],
    "triggered": false,
    "triggered_by": [],
    "triggers": [],
    "unless": "",
    "when_creating": {}
}
""".lstrip())


def test_bw_items_invocation_single_item_preview(tmpdir):
    _bw_items_invocation_make_repo(tmpdir)
    _test_bw_items_invocation_succeeds(tmpdir, 'bw items --preview node1 file:/foo/bar/moo', """
bar
""".lstrip())
