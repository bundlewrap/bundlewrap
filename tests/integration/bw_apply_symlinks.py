from os import mkdir, readlink, symlink
from os.path import join

from bundlewrap.utils.testing import host_os, make_repo, run


def test_create(tmpdir):
    make_repo(
        tmpdir,
        bundles={
            "test": {
                'items': {
                    'symlinks': {
                        join(str(tmpdir), "foo"): {
                            'target': "/dev/null",
                        },
                    },
                },
            },
        },
        nodes={
            "localhost": {
                'bundles': ["test"],
                'os': host_os(),
            },
        },
    )
    stdout, stderr, rcode = run("bw apply localhost", path=str(tmpdir))
    assert rcode == 0
    assert readlink(join(str(tmpdir), "foo")) == "/dev/null"


def test_fix(tmpdir):
    symlink(join(str(tmpdir), "bar"), join(str(tmpdir), "foo"))
    make_repo(
        tmpdir,
        bundles={
            "test": {
                'items': {
                    'symlinks': {
                        join(str(tmpdir), "foo"): {
                            'target': "/dev/null",
                        },
                    },
                },
            },
        },
        nodes={
            "localhost": {
                'bundles': ["test"],
                'os': host_os(),
            },
        },
    )
    stdout, stderr, rcode = run("bw apply localhost", path=str(tmpdir))
    assert rcode == 0
    assert readlink(join(str(tmpdir), "foo")) == "/dev/null"


def test_fix_dir(tmpdir):
    mkdir(join(str(tmpdir), "foo"))
    make_repo(
        tmpdir,
        bundles={
            "test": {
                'items': {
                    'symlinks': {
                        join(str(tmpdir), "foo"): {
                            'target': "/dev/null",
                        },
                    },
                },
            },
        },
        nodes={
            "localhost": {
                'bundles': ["test"],
                'os': host_os(),
            },
        },
    )
    stdout, stderr, rcode = run("bw apply localhost", path=str(tmpdir))
    assert rcode == 0
    assert readlink(join(str(tmpdir), "foo")) == "/dev/null"


def test_fix_dir_target(tmpdir):
    mkdir(join(str(tmpdir), "dir1"))
    mkdir(join(str(tmpdir), "dir2"))
    symlink(join(str(tmpdir), "dir1"), join(str(tmpdir), "link"))
    make_repo(
        tmpdir,
        bundles={
            "test": {
                'items': {
                    'symlinks': {
                        join(str(tmpdir), "link"): {
                            'target': join(str(tmpdir), "dir2"),
                        },
                    },
                },
            },
        },
        nodes={
            "localhost": {
                'bundles': ["test"],
                'os': host_os(),
            },
        },
    )
    stdout, stderr, rcode = run("bw apply localhost", path=str(tmpdir))
    assert rcode == 0
    assert readlink(join(str(tmpdir), "link")) == join(str(tmpdir), "dir2")
