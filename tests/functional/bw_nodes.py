from bundlewrap.cmdline import main
from bundlewrap.utils.testing import make_repo
from bundlewrap.utils.ui import io


def test_empty(tmpdir):
    make_repo(tmpdir)
    with io.capture() as captured:
        main("nodes", path=str(tmpdir))
    assert captured['stdout'] == ""
    assert captured['stderr'] == ""


def test_single(tmpdir):
    make_repo(tmpdir, nodes={"node1": {}})
    with io.capture() as captured:
        main("nodes", path=str(tmpdir))
    assert captured['stdout'] == "node1\n"
    assert captured['stderr'] == ""


def test_hostname(tmpdir):
    make_repo(tmpdir, nodes={"node1": {'hostname': "node1.example.com"}})
    with io.capture() as captured:
        main("nodes", "--hostnames", path=str(tmpdir))
    assert captured['stdout'] == "node1.example.com\n"
    assert captured['stderr'] == ""


def test_in_group(tmpdir):
    make_repo(
        tmpdir,
        groups={
            "group1": {
                'members': ["node2"],
            },
        },
        nodes={
            "node1": {},
            "node2": {},
        },
    )
    with io.capture() as captured:
        main("nodes", "-g", "group1", path=str(tmpdir))
    assert captured['stdout'] == "node2\n"
    assert captured['stderr'] == ""


def test_bundles(tmpdir):
    make_repo(
        tmpdir,
        bundles={
            "bundle1": {},
            "bundle2": {},
        },
        nodes={
            "node1": {'bundles': ["bundle1", "bundle2"]},
            "node2": {'bundles': ["bundle2"]},
        },
    )
    with io.capture() as captured:
        main("nodes", "--bundles", path=str(tmpdir))
    assert captured['stdout'].strip().split("\n") == [
        "node1: bundle1, bundle2",
        "node2: bundle2",
    ]
    assert captured['stderr'] == ""


def test_groups(tmpdir):
    make_repo(
        tmpdir,
        groups={
            "group1": {
                'members': ["node2"],
            },
        },
        nodes={
            "node1": {},
            "node2": {},
        },
    )
    with io.capture() as captured:
        main("nodes", "--groups", path=str(tmpdir))
    assert captured['stdout'].strip().split("\n") == [
        "node1: ",
        "node2: group1",
    ]
    assert captured['stderr'] == ""
