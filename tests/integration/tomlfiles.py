from os.path import join

from bundlewrap.repo import Repository
from bundlewrap.utils import get_file_contents
from bundlewrap.utils.testing import make_repo


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

    # str is needed on Python 3.5 for LocalPath objects
    assert get_file_contents(join(str(tmpdir), "nodes", "node1.toml")) == \
        b"""os = "ubuntu"

[metadata.foo]
bar = "baz"
"""
