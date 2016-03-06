from os.path import join

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
    io.stdout("fin")

def test_node(repo, node, **kwargs):
    io.stdout(node.name)
""")
    assert run("bw test", path=str(tmpdir))[0] in (
        b"node1\nnode2\nfin\n",
        b"node2\nnode1\nfin\n",
    )


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
