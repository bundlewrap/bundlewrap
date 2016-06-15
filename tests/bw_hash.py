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


def test_metadata_empty(tmpdir):
    make_repo(
        tmpdir,
        nodes={
            "node1": {
                'metadata': {},
            },
        },
    )

    stdout, stderr, rcode = run("bw hash -m node1", path=str(tmpdir))
    assert rcode == 0
    assert stdout == b"bf21a9e8fbc5a3846fb05b4fa0859e0917b2202f\n"


def test_metadata_nested_sort(tmpdir):
    make_repo(
        tmpdir,
        nodes={
            "node1": {
                'metadata': {
                    'nested': {
                        'one': True,
                        'two': False,
                        'three': 3,
                        'four': "four",
                        'five': None,
                    },
                },
            },
            "node2": {
                'metadata': {
                    'nested': {
                        'five': None,
                        'four': "four",
                        'one': True,
                        'three': 3,
                        'two': False,
                    },
                },
            },
        },
    )

    stdout1, stderr, rcode = run("bw hash -m node1", path=str(tmpdir))
    assert rcode == 0
    assert stdout1 == b"bc403a093ca3399cd3efa7a64ec420e0afef5e70\n"

    stdout2, stderr, rcode = run("bw hash -m node2", path=str(tmpdir))
    assert rcode == 0
    assert stdout1 == stdout2


def test_metadata_repo(tmpdir):
    make_repo(
        tmpdir,
        nodes={
            "node1": {
                'metadata': {
                    'foo': 47,
                },
            },
        },
    )

    stdout, stderr, rcode = run("bw hash -m", path=str(tmpdir))
    assert rcode == 0
    assert stdout == b"c0cc160ab1b6e71155cd4f65139bc7f66304d7f3\n"


def test_metadata_repo_dict(tmpdir):
    make_repo(
        tmpdir,
        nodes={
            "node1": {
                'metadata': {
                    'foo': 47,
                },
            },
        },
    )

    stdout, stderr, rcode = run("bw hash -md", path=str(tmpdir))
    assert rcode == 0
    assert stdout == b"node1\t013b3a8199695eb45c603ea4e0a910148d80e7ed\n"
