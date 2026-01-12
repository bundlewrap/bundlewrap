from os.path import exists

from bundlewrap.utils.testing import host_os, make_repo, run


def test_if_blocks_item(tmpdir):
    make_repo(
        tmpdir,
        bundles={
            "test": {
                'items': {
                    'actions': {
                        "guarded": {
                            'command': "false",
                            'if': "false",
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


def test_if_and_unless_combined(tmpdir):
    marker = tmpdir.join("ran")

    make_repo(
        tmpdir,
        bundles={
            "test": {
                'items': {
                    'actions': {
                        "gated": {
                            'command': f"touch {marker}",
                            'if': "true",
                            'unless': "false",
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
    assert exists(str(marker))


def test_if_fails_skips_even_without_unless(tmpdir):
    make_repo(
        tmpdir,
        bundles={
            "test": {
                'items': {
                    'actions': {
                        "if_fails": {
                            'command': "false",
                            'if': "false",
                            'unless': "false",
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
