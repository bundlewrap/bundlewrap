from base64 import b64encode
from os.path import exists, join

from bundlewrap.utils.testing import host_os, make_repo, run


def test_any_content_create(tmpdir):
    make_repo(
        tmpdir,
        bundles={
            "test": {
                'items': {
                    'files': {
                        join(str(tmpdir), "foo"): {
                            'content_type': 'any',
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

    run("bw apply localhost", path=str(tmpdir))
    with open(join(str(tmpdir), "foo"), 'rb') as f:
        content = f.read()
    assert content == b""


def test_any_content_exists(tmpdir):
    make_repo(
        tmpdir,
        bundles={
            "test": {
                'items': {
                    'files': {
                        join(str(tmpdir), "foo"): {
                            'content_type': 'any',
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
    with open(join(str(tmpdir), "foo"), 'wb') as f:
        f.write(b"existing content")

    run("bw apply localhost", path=str(tmpdir))
    with open(join(str(tmpdir), "foo"), 'rb') as f:
        content = f.read()
    assert content == b"existing content"


def test_binary_inline_content(tmpdir):
    make_repo(
        tmpdir,
        bundles={
            "test": {
                'items': {
                    'files': {
                        join(str(tmpdir), "foo.bin"): {
                            'content_type': 'base64',
                            'content': b64encode("ö".encode('latin-1')),
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
    run("bw apply localhost", path=str(tmpdir))
    with open(join(str(tmpdir), "foo.bin"), 'rb') as f:
        content = f.read()
    assert content.decode('latin-1') == "ö"


def test_binary_template_content(tmpdir):
    make_repo(
        tmpdir,
        bundles={
            "test": {
                'items': {
                    'files': {
                        join(str(tmpdir), "foo.bin"): {
                            'encoding': 'latin-1',
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
    with open(join(str(tmpdir), "bundles", "test", "files", "foo.bin"), 'wb') as f:
        f.write("ö".encode('utf-8'))

    run("bw apply localhost", path=str(tmpdir))
    with open(join(str(tmpdir), "foo.bin"), 'rb') as f:
        content = f.read()
    assert content.decode('latin-1') == "ö"


def test_delete(tmpdir):
    with open(join(str(tmpdir), "foo"), 'w') as f:
        f.write("foo")
    make_repo(
        tmpdir,
        bundles={
            "test": {
                'items': {
                    'files': {
                        join(str(tmpdir), "foo"): {
                            'delete': True,
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
    run("bw apply localhost", path=str(tmpdir))
    assert not exists(join(str(tmpdir), "foo"))


def test_mako_template_content(tmpdir):
    make_repo(
        tmpdir,
        bundles={
            "test": {
                'items': {
                    'files': {
                        join(str(tmpdir), "foo"): {
                            'content_type': 'mako',
                            'content': "${node.name}",
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
    run("bw apply localhost", path=str(tmpdir))
    with open(join(str(tmpdir), "foo"), 'rb') as f:
        content = f.read()
    assert content == b"localhost"


def test_mako_template_content_with_secret(tmpdir):
    make_repo(
        tmpdir,
        bundles={
            "test": {
                'items': {
                    'files': {
                        join(str(tmpdir), "foo"): {
                            'content_type': 'mako',
                            'content': "${repo.vault.password_for('testing')}",
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
    run("bw apply localhost", path=str(tmpdir))
    with open(join(str(tmpdir), "foo"), 'rb') as f:
        content = f.read()
    assert content == b"faCTT76kagtDuZE5wnoiD1CxhGKmbgiX"


def test_text_template_content(tmpdir):
    make_repo(
        tmpdir,
        bundles={
            "test": {
                'items': {
                    'files': {
                        join(str(tmpdir), "foo"): {
                            'content_type': 'text',
                            'content': "${node.name}",
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
    run("bw apply localhost", path=str(tmpdir))
    with open(join(str(tmpdir), "foo"), 'rb') as f:
        content = f.read()
    assert content == b"${node.name}"


def test_fault_content_unavailable_skipped(tmpdir):
    make_repo(
        tmpdir,
        bundles={
            "test": {
                'items': {},
            },
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
files = {
    "/tmp/bw_test_faultunavailable": {
        'content': repo.vault.password_for("fault", key="missing"),
    },
}
""")
    stdout, stderr, rcode = run("bw apply localhost", path=str(tmpdir))
    assert rcode == 0
    assert b"file:/tmp/bw_test_faultunavailable skipped (Fault unavailable)" in stdout
    assert not exists("/tmp/bw_test_faultunavailable")
