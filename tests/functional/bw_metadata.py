from json import loads
from os.path import join

from bundlewrap.cmdline import main
from bundlewrap.utils.testing import make_repo
from bundlewrap.utils.ui import io


def test_empty(tmpdir):
    make_repo(
        tmpdir,
        nodes={
            "node1": {},
        },
    )
    with io.capture() as captured:
        main("metadata", "node1", path=str(tmpdir))
    assert captured['stdout'] == "{}\n"
    assert captured['stderr'] == ""


def test_simple(tmpdir):
    make_repo(
        tmpdir,
        nodes={
            "node1": {'metadata': {"foo": "bar"}},
        },
    )
    with io.capture() as captured:
        main("metadata", "node1", path=str(tmpdir))
    assert loads(captured['stdout']) == {"foo": "bar"}
    assert captured['stderr'] == ""


def test_merge(tmpdir):
    make_repo(
        tmpdir,
        nodes={
            "node1": {
                'metadata': {
                    "foo": {
                        "bar": "baz",
                    },
                },
            },
        },
        groups={
            "group1": {
                'members': ["node1"],
                'metadata': {
                    "ding": 5,
                    "foo": {
                        "bar": "ZAB",
                        "baz": "bar",
                    },
                },
            },
        },
    )
    with io.capture() as captured:
        main("metadata", "node1", path=str(tmpdir))
    assert loads(captured['stdout']) == {
        "ding": 5,
        "foo": {
            "bar": "baz",
            "baz": "bar",
        },
    }
    assert captured['stderr'] == ""


def test_metadatapy(tmpdir):
    make_repo(
        tmpdir,
        bundles={"test": {}},
        nodes={
            "node1": {
                'bundles': ["test"],
                'metadata': {"foo": "bar"},
            },
        },
    )
    with open(join(str(tmpdir), "bundles", "test", "metadata.py"), 'w') as f:
        f.write(
"""def foo(metadata):
    if "baz" in metadata:
        return None
    else:
        metadata["baz"] = 47
""")
    with io.capture() as captured:
        main("metadata", "node1", path=str(tmpdir))
    assert loads(captured['stdout']) == {
        "baz": 47,
        "foo": "bar",
    }
    assert captured['stderr'] == ""
