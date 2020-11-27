from os.path import exists, join

from bundlewrap.utils.testing import host_os, make_repo, run


def test_skip_bundle(tmpdir):
    make_repo(
        tmpdir,
        bundles={
            "test": {
                'items': {
                    'files': {
                        join(str(tmpdir), "foo"): {
                            'content': "nope",
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
    result = run("bw apply --skip bundle:test -- localhost", path=str(tmpdir))
    assert result[2] == 0
    assert not exists(join(str(tmpdir), "foo"))


def test_skip_group(tmpdir):
    make_repo(
        tmpdir,
        bundles={
            "test": {
                'items': {
                    'files': {
                        join(str(tmpdir), "foo"): {
                            'content': "nope",
                        },
                    },
                },
            },
        },
        nodes={
            "localhost": {
                'bundles': ["test"],
                'groups': {"foo"},
                'os': host_os(),
            },
        },
        groups={
            "foo": {},
        },
    )
    result = run("bw apply --skip group:foo -- localhost", path=str(tmpdir))
    assert result[2] == 0
    assert not exists(join(str(tmpdir), "foo"))


def test_skip_id(tmpdir):
    make_repo(
        tmpdir,
        bundles={
            "test": {
                'items': {
                    'files': {
                        join(str(tmpdir), "foo"): {
                            'content': "nope",
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
    result = run("bw apply --skip file:{} -- localhost".format(join(str(tmpdir), "foo")), path=str(tmpdir))
    assert result[2] == 0
    assert not exists(join(str(tmpdir), "foo"))


def test_skip_node(tmpdir):
    make_repo(
        tmpdir,
        bundles={
            "test": {
                'items': {
                    'files': {
                        join(str(tmpdir), "foo"): {
                            'content': "nope",
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
    result = run("bw apply --skip node:localhost -- localhost", path=str(tmpdir))
    assert result[2] == 0
    assert not exists(join(str(tmpdir), "foo"))


def test_skip_tag(tmpdir):
    make_repo(
        tmpdir,
        bundles={
            "test": {
                'items': {
                    'files': {
                        join(str(tmpdir), "foo"): {
                            'content': "nope",
                            'tags': ["nope"],
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
    result = run("bw apply --skip tag:nope -- localhost", path=str(tmpdir))
    assert result[2] == 0
    assert not exists(join(str(tmpdir), "foo"))


def test_skip_type(tmpdir):
    make_repo(
        tmpdir,
        bundles={
            "test": {
                'items': {
                    'files': {
                        join(str(tmpdir), "foo"): {
                            'content': "nope",
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
    result = run("bw apply --skip file: -- localhost", path=str(tmpdir))
    assert result[2] == 0
    assert not exists(join(str(tmpdir), "foo"))


def test_skip_trigger(tmpdir):
    make_repo(
        tmpdir,
        bundles={
            "test": {
                'items': {
                    'files': {
                        join(str(tmpdir), "foo"): {
                            'content': "nope",
                            'tags': ["nope"],
                            'triggers': ["file:{}".format(join(str(tmpdir), "bar"))],
                        },
                        join(str(tmpdir), "bar"): {
                            'content': "nope",
                            'triggered': True,
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
    result = run("bw apply --skip tag:nope -- localhost", path=str(tmpdir))
    assert result[2] == 0
    assert not exists(join(str(tmpdir), "foo"))
    assert not exists(join(str(tmpdir), "bar"))
