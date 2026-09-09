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
    with open(join(tmpdir, "magic_strings.py"), 'w') as f:
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
    with open(join(tmpdir, "magic_strings.py"), 'w') as f:
        f.write(dedent("""
        @magic_string
        def magic(arg):
            return "converted magic string"
        """))

    stdout, stderr, rcode = run("bw nodes -a username", path=str(tmpdir))
    assert b"converted magic string" in stdout
    assert stderr == b""
    assert rcode == 0


def _magic_strings(tmpdir, source):
    with open(join(tmpdir, "magic_strings.py"), 'w') as f:
        f.write(dedent(source))


def test_magic_string_receives_node(tmpdir):
    make_repo(
        tmpdir,
        groups={
            "group1": {"generate_key": "command"},
        },
        nodes={
            "node1": {"groups": ["group1"], "password": "!password_for:testing"},
            "node2": {"password": "!password_for:testing"},
        },
    )
    _magic_strings(tmpdir, """
        @magic_string
        def password_for(identifier, node=None):
            return (node.vault if node else vault).password_for(identifier)
    """)

    stdout, stderr, rcode = run("bw debug -n node2 -c 'print(node.password)'", path=str(tmpdir))
    assert stdout == b"faCTT76kagtDuZE5wnoiD1CxhGKmbgiX\n"
    assert stderr == b""
    assert rcode == 0

    stdout, stderr, rcode = run(
        "bw debug -n node1 -c 'print(str(node.password) == "
        "str(repo.vault.password_for(\"testing\", key=\"encrypt\")))'",
        path=str(tmpdir),
    )
    assert stdout == b"True\n"
    assert stderr == b""
    assert rcode == 0


def test_magic_string_in_group_file_gets_no_node(tmpdir):
    make_repo(
        tmpdir,
        groups={
            "group1": {"username": "!whoami:"},
        },
        nodes={
            "node1": {"groups": ["group1"], "password": "!whoami:"},
        },
    )
    _magic_strings(tmpdir, """
        @magic_string
        def whoami(arg, node=None):
            return "node {}".format(node.name) if node else "group"
    """)

    stdout, stderr, rcode = run(
        "BW_TABLE_STYLE=grep bw nodes -a username password",
        path=str(tmpdir),
    )
    assert stdout == b"node1\tgroup\tnode node1\n"
    assert stderr == b""
    assert rcode == 0


def test_magic_string_explicit_name(tmpdir):
    make_repo(
        tmpdir,
        nodes={
            "node1": {"username": "!32_random_bytes_as_base64_for:foo"},
        },
    )
    _magic_strings(tmpdir, """
        @magic_string(name="32_random_bytes_as_base64_for")
        def random_bytes(identifier):
            return vault.random_bytes_as_base64_for(identifier)
    """)

    stdout, stderr, rcode = run("BW_TABLE_STYLE=grep bw nodes -a username", path=str(tmpdir))
    assert stdout == b"node1\trt+Dgv0yA10DS3ux94mmtEg+isChTJvgkfklzmWkvyg=\n"
    assert stderr == b""
    assert rcode == 0


def test_magic_string_node_attribute_not_available(tmpdir):
    make_repo(
        tmpdir,
        nodes={
            "node1": {"generate_key": "generate", "username": "!keyname:"},
        },
    )
    _magic_strings(tmpdir, """
        @magic_string
        def keyname(arg, node=None):
            return node.generate_key
    """)

    stdout, stderr, rcode = run("bw nodes -a username", path=str(tmpdir))
    assert rcode != 0
    assert b"attribute 'generate_key' of node 'node1' is not available yet" in stderr


def test_magic_string_duplicate_name(tmpdir):
    make_repo(tmpdir, nodes={"node1": {}})
    _magic_strings(tmpdir, """
        @magic_string
        def foo(arg):
            return arg

        @magic_string(name="foo")
        def bar(arg):
            return arg
    """)

    stdout, stderr, rcode = run("bw nodes", path=str(tmpdir))
    assert rcode != 0
    assert b"magic string 'foo' defined more than once" in stderr


def test_magic_string_invalid_name(tmpdir):
    make_repo(tmpdir, nodes={"node1": {}})
    _magic_strings(tmpdir, """
        @magic_string(name="no:colons")
        def foo(arg):
            return arg
    """)

    stdout, stderr, rcode = run("bw nodes", path=str(tmpdir))
    assert rcode != 0
    assert b"invalid magic string name 'no:colons'" in stderr


def test_magic_string_positional_name(tmpdir):
    make_repo(tmpdir, nodes={"node1": {}})
    _magic_strings(tmpdir, """
        @magic_string("foo")
        def bar(arg):
            return arg
    """)

    stdout, stderr, rcode = run("bw nodes", path=str(tmpdir))
    assert rcode != 0
    assert b"takes no positional argument" in stderr
