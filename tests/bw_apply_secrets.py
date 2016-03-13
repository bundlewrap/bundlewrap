# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from os.path import exists, join

from bundlewrap.utils.testing import host_os, make_repo, run


def test_fault_content(tmpdir):
    make_repo(
        tmpdir,
        bundles={
            "test": {},
        },
        nodes={
            "localhost": {
                'bundles': ["test"],
                'os': host_os(),
            },
        },
    )

    with open(join(str(tmpdir), "bundles", "test", "items.py"), 'w') as f:
        f.write("""
files = {{
    "{}": {{
        'content': repo.vault.password_for("test"),
    }},
}}
""".format(join(str(tmpdir), "secret")))

    run("bw apply localhost", path=str(tmpdir))
    with open(join(str(tmpdir), "secret")) as f:
        content = f.read()
    assert content == "Q4WeYdfKaSOOPF8pz13z7yRbjJ6HD7ZB"


def test_fault_content_mako(tmpdir):
    make_repo(
        tmpdir,
        bundles={
            "test": {
                'files': {
                    join(str(tmpdir), "secret"): {
                        'content': "${repo.vault.password_for('test')}",
                        'content_type': 'mako',
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

    run("bw apply localhost", path=str(tmpdir))
    with open(join(str(tmpdir), "secret")) as f:
        content = f.read()
    assert content == "Q4WeYdfKaSOOPF8pz13z7yRbjJ6HD7ZB"


def test_fault_content_jinja2(tmpdir):
    make_repo(
        tmpdir,
        bundles={
            "test": {
                'files': {
                    join(str(tmpdir), "secret"): {
                        'content': "{{ repo.vault.password_for('test') }}",
                        'content_type': 'jinja2',
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

    run("bw apply localhost", path=str(tmpdir))
    with open(join(str(tmpdir), "secret")) as f:
        content = f.read()
    assert content == "Q4WeYdfKaSOOPF8pz13z7yRbjJ6HD7ZB"


def test_fault_content_skipped(tmpdir):
    make_repo(
        tmpdir,
        bundles={
            "test": {},
        },
        nodes={
            "localhost": {
                'bundles': ["test"],
                'os': host_os(),
            },
        },
    )

    with open(join(str(tmpdir), "bundles", "test", "items.py"), 'w') as f:
        f.write("""
files = {{
    "{}": {{
        'content': repo.vault.password_for("test", key='unavailable'),
    }},
}}
""".format(join(str(tmpdir), "secret")))

    stdout, stderr, rcode = run("bw apply localhost", path=str(tmpdir))
    assert rcode == 0
    assert not exists(join(str(tmpdir), "secret"))


def test_fault_content_skipped_mako(tmpdir):
    make_repo(
        tmpdir,
        bundles={
            "test": {
                'files': {
                    join(str(tmpdir), "secret"): {
                        'content': "${repo.vault.password_for('test', key='unavailable')}",
                        'content_type': 'mako',
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
    assert not exists(join(str(tmpdir), "secret"))


def test_fault_content_skipped_jinja2(tmpdir):
    make_repo(
        tmpdir,
        bundles={
            "test": {
                'files': {
                    join(str(tmpdir), "secret"): {
                        'content': "{{ repo.vault.password_for('test', key='unavailable') }}",
                        'content_type': 'jinja2',
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


def test_fault_content_error(tmpdir):
    make_repo(
        tmpdir,
        bundles={
            "test": {},
        },
        nodes={
            "localhost": {
                'bundles': ["test"],
                'os': host_os(),
            },
        },
    )

    with open(join(str(tmpdir), "bundles", "test", "items.py"), 'w') as f:
        f.write("""
files = {{
    "{}": {{
        'content': repo.vault.password_for("test", key='unavailable'),
        'error_on_missing_fault': True,
    }},
}}
""".format(join(str(tmpdir), "secret")))

    stdout, stderr, rcode = run("bw -d apply localhost", path=str(tmpdir))
    print(stdout)
    assert rcode == 1
