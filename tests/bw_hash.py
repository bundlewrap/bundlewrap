from bundlewrap.utils.testing import make_repo, run


def test_empty(tmpdir):
    make_repo(tmpdir)
    stdout, stderr, rcode = run("bw hash", path=str(tmpdir))
    assert stdout == b"bf21a9e8fbc5a3846fb05b4fa0859e0917b2202f\n"
    assert stderr == b""


def test_nondeterministic(tmpdir):
    make_repo(
        tmpdir,
        nodes={
            "node1": {
                'bundles': ["bundle1"],
            },
        },
        bundles={
            "bundle1": {
                'files': {
                    "/test": {
                        'content_type': 'mako',
                        'content': "<% import random %>${random.randint(1, 9999)}",
                    },
                },
            },
        },
    )

    hashes = set()

    for i in range(3):
        stdout, stderr, rcode = run("bw hash", path=str(tmpdir))
        hashes.add(stdout.strip())

    assert len(hashes) > 1


def test_deterministic(tmpdir):
    make_repo(
        tmpdir,
        nodes={
            "node1": {
                'bundles': ["bundle1"],
            },
        },
        bundles={
            "bundle1": {
                'files': {
                    "/test": {
                        'content': "${node.name}",
                    },
                },
            },
        },
    )

    hashes = set()

    for i in range(3):
        stdout, stderr, rcode = run("bw hash", path=str(tmpdir))
        hashes.add(stdout.strip())

    assert len(hashes) == 1
    assert hashes.pop() == b"8c155b4e7056463eb2c8a8345f4f316f6d7359f6"


def test_dict(tmpdir):
    make_repo(
        tmpdir,
        nodes={
            "node1": {
                'bundles': ["bundle1"],
            },
        },
        bundles={
            "bundle1": {
                'files': {
                    "/test": {
                        'content': "yes please",
                    },
                },
            },
        },
    )

    stdout, stderr, rcode = run("bw hash -d", path=str(tmpdir))
    assert rcode == 0
    assert stdout == b"8ab35c696b63a853ccf568b27a50e24a69964487  node1\n"

    stdout, stderr, rcode = run("bw hash -d node1", path=str(tmpdir))
    assert rcode == 0
    assert stdout == b"503583964eadabacb18fda32cc9fb1e9f66e424b  file:/test\n"

    stdout, stderr, rcode = run("bw hash -d node1 file:/test", path=str(tmpdir))
    assert rcode == 0
    assert stdout == (
        b"content_hash\tc05a36d547e2b1682472f76985018038d1feebc5\n"
        b"type\tfile\n"
    )
