import pytest

from bundlewrap.cmdline import main
from bundlewrap.utils.testing import make_repo
from bundlewrap.utils.ui import io


def test_empty(tmpdir):
    make_repo(tmpdir)
    with io.capture() as captured:
        main("test", path=str(tmpdir))
    assert captured['stdout'] == ""


def test_bundle_not_found(tmpdir):
    make_repo(
        tmpdir,
        nodes={
            "node1": {
                'bundles': ["bundle1"],
            },
        },
    )
    with pytest.raises(SystemExit):
        main("test", path=str(tmpdir))


#def test_circular_dep_direct(tmpdir):
#    make_repo(
#        tmpdir,
#        nodes={
#            "node1": {
#                'bundles': ["bundle1"],
#            },
#        },
#        bundles={
#            "bundle1": {
#                "pkg_apt": {
#                    "foo": {
#                        'needs': ["pkg_apt:bar"],
#                    },
#                    "bar": {
#                        'needs': ["pkg_apt:foo"],
#                    },
#                },
#            },
#        },
#    )
#    with pytest.raises(SystemExit):
#        main("test", path=str(tmpdir))
#
#
#def test_circular_dep_indirect(tmpdir):
#    make_repo(
#        tmpdir,
#        nodes={
#            "node1": {
#                'bundles': ["bundle1"],
#            },
#        },
#        bundles={
#            "bundle1": {
#                "pkg_apt": {
#                    "foo": {
#                        'needs': ["pkg_apt:bar"],
#                    },
#                    "bar": {
#                        'needs': ["pkg_apt:baz"],
#                    },
#                    "baz": {
#                        'needs': ["pkg_apt:foo"],
#                    },
#                },
#            },
#        },
#    )
#    with pytest.raises(SystemExit):
#        main("test", path=str(tmpdir))
#
#
#def test_circular_dep_self(tmpdir):
#    make_repo(
#        tmpdir,
#        nodes={
#            "node1": {
#                'bundles': ["bundle1"],
#            },
#        },
#        bundles={
#            "bundle1": {
#                "pkg_apt": {
#                    "foo": {
#                        'needs': ["pkg_apt:foo"],
#                    },
#                },
#            },
#        },
#    )
#    with pytest.raises(SystemExit):
#        main("test", path=str(tmpdir))


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
    with pytest.raises(SystemExit):
        main("test", path=str(tmpdir))


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
    with pytest.raises(SystemExit):
        main("test", path=str(tmpdir))
