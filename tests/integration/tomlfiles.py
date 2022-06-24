from os import makedirs
from os.path import join

from bundlewrap.repo import Repository
from bundlewrap.utils import get_file_contents
from bundlewrap.utils.testing import make_repo, run


def test_toml_conversion(tmpdir):
    make_repo(
        tmpdir,
        nodes={
            'node1': {
                'os': 'ubuntu',
                'metadata': {
                    "foo": {
                        "bar": "baz",
                    },
                },
            },
        },
    )
    repo = Repository(tmpdir)
    node = repo.get_node("node1")
    node.toml_save()

    assert get_file_contents(join(tmpdir, "nodes", "node1.toml")) == \
        b"""os = "ubuntu"

[metadata.foo]
bar = "baz"
"""


def test_duplicate_nodes(tmpdir):
    make_repo(tmpdir)
    makedirs(join(tmpdir, "nodes", "aaa"))
    makedirs(join(tmpdir, "nodes", "bbb"))
    with open(join(tmpdir, "nodes", "aaa", "node1.toml"), 'w') as f:
        f.write("")
    with open(join(tmpdir, "nodes", "bbb", "node1.toml"), 'w') as f:
        f.write("")

    stdout, stderr, rcode = run("bw nodes", path=str(tmpdir))
    assert "aaa" in stderr.decode()
    assert "bbb" in stderr.decode()
    assert rcode == 1
