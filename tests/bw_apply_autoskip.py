# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from os.path import exists, join

from bundlewrap.utils.testing import host_os, make_repo, run


def test_skip_bundle(tmpdir):
    make_repo(
        tmpdir,
        bundles={
            "test": {
                'files': {
                    join(str(tmpdir), "foo"): {
                        'content': "nope",
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
    run("bw apply --skip bundle:test localhost", path=str(tmpdir))
    assert not exists(join(str(tmpdir), "foo"))


def test_skip_group(tmpdir):
    make_repo(
        tmpdir,
        bundles={
            "test": {
                'files': {
                    join(str(tmpdir), "foo"): {
                        'content': "nope",
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
        groups={
            "foo": {'members': ["localhost"]},
        },
    )
    run("bw apply --skip group:foo localhost", path=str(tmpdir))
    assert not exists(join(str(tmpdir), "foo"))


def test_skip_node(tmpdir):
    make_repo(
        tmpdir,
        bundles={
            "test": {
                'files': {
                    join(str(tmpdir), "foo"): {
                        'content': "nope",
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
    run("bw apply --skip node:localhost localhost", path=str(tmpdir))
    assert not exists(join(str(tmpdir), "foo"))


def test_skip_tag(tmpdir):
    make_repo(
        tmpdir,
        bundles={
            "test": {
                'files': {
                    join(str(tmpdir), "foo"): {
                        'content': "nope",
                        'tags': ["nope"],
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
    run("bw apply --skip tag:nope localhost", path=str(tmpdir))
    assert not exists(join(str(tmpdir), "foo"))


def test_skip_type(tmpdir):
    make_repo(
        tmpdir,
        bundles={
            "test": {
                'files': {
                    join(str(tmpdir), "foo"): {
                        'content': "nope",
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
    run("bw apply --skip file: localhost", path=str(tmpdir))
    assert not exists(join(str(tmpdir), "foo"))
