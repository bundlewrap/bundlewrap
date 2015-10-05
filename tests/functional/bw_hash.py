from bundlewrap.cmdline import main
from bundlewrap.utils.testing import make_repo
from bundlewrap.utils.ui import io


def test_empty(tmpdir):
    make_repo(tmpdir)
    with io.capture() as captured:
        main("hash", path=str(tmpdir))
    assert captured['stdout'] == "bf21a9e8fbc5a3846fb05b4fa0859e0917b2202f\n"
    assert captured['stderr'] == ""


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
        with io.capture() as captured:
            main("hash", path=str(tmpdir))
        hashes.add(captured['stdout'].strip())

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
        with io.capture() as captured:
            main("hash", path=str(tmpdir))
        hashes.add(captured['stdout'].strip())

    assert len(hashes) == 1
    assert hashes.pop() == "4b3081d0916a16101afcc03d5e8c29e22e9b9efc"
