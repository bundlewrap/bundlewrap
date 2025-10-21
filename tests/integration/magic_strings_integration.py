from os.path import join
from textwrap import dedent

from bundlewrap.utils.testing import make_repo, run

# Most of this is already tested in unit tests. Here, we only test that
# magic strings actually work inside nodes and groups.

def test_magic_string_in_node_file(tmpdir):
    make_repo(
        tmpdir,
        nodes={
            "node1": {
                "username": "!magic:dummy"
            },
        },
    )
    with open(join(tmpdir, "magic-strings.py"), 'w') as f:
        f.write(dedent("""
        @magic_string
        def magic(arg):
            return "converted magic string"
        """))

    stdout, stderr, rcode = run("bw nodes -a username", path=str(tmpdir))
    assert b"converted magic string" in stdout
    assert stderr == b""
    assert rcode == 0


def test_magic_string_in_group_file(tmpdir):
    make_repo(
        tmpdir,
        groups={
            "group1": {
                "username": "!magic:dummy"
            },
        },
        nodes={
            "node1": {
                "groups": ["group1"],
            },
        },
    )
    with open(join(tmpdir, "magic-strings.py"), 'w') as f:
        f.write(dedent("""
        @magic_string
        def magic(arg):
            return "converted magic string"
        """))

    stdout, stderr, rcode = run("bw nodes -a username", path=str(tmpdir))
    assert b"converted magic string" in stdout
    assert stderr == b""
    assert rcode == 0