from os.path import join

from bundlewrap.utils.testing import make_repo, run


def test_metadata(tmpdir):
    make_repo(
        tmpdir,
        nodes={
            "node1": {'metadata': {"key": "value1"}},
            "node2": {'metadata': {"key": "value2"}},
        },
    )
    stdout, stderr, rcode = run("bw diff -m node1 node2", path=str(tmpdir))
    assert b"value1" in stdout
    assert b"value2" in stdout
    assert stderr == b""
    assert rcode == 0


def test_file_items(tmpdir):
    make_repo(
        tmpdir,
        nodes={
            "node1": {'bundles': ["bundle1"]},
            "node2": {'bundles': ["bundle2"]},
        },
        bundles={
            "bundle1": {
                'items': {
                    "files": {
                        "/tmp/test": {
                            'content': "one",
                        },
                    },
                },
            },
            "bundle2": {
                'items': {
                    "files": {
                        "/tmp/test": {
                            'content': "two",
                        },
                    },
                },
            },
        },
    )
    stdout, stderr, rcode = run("bw diff -i file:/tmp/test -- node1 node2", path=str(tmpdir))
    assert b"one" in stdout
    assert b"two" in stdout
    assert stderr == b""
    assert rcode == 0


def test_whole_node(tmpdir):
    make_repo(
        tmpdir,
        nodes={
            "node1": {'bundles': ["bundle1", "bundle3"]},
            "node2": {'bundles': ["bundle2", "bundle3"]},
        },
        bundles={
            "bundle1": {
                'items': {
                    "files": {
                        "/tmp/foo": {
                            'content': "one",
                        },
                    },
                },
            },
            "bundle2": {
                'items': {
                    "files": {
                        "/tmp/foo": {
                            'content': "two",
                        },
                    },
                },
            },
            "bundle3": {
                'items': {
                    "files": {
                        "/tmp/bar": {
                            'content': "common",
                        },
                    },
                },
            },
        },
    )
    stdout, stderr, rcode = run("bw diff node1 node2", path=str(tmpdir))
    assert b"/tmp/foo" in stdout
    assert b"/tmp/bar" not in stdout
    assert stderr == b""
    assert rcode == 0


def test_fault_unavailable(tmpdir):
    make_repo(
        tmpdir,
        nodes={
            "node1": {'bundles': ["bundle1", "bundle3"]},
            "node2": {'bundles': ["bundle2", "bundle3"]},
        },
        bundles={
            "bundle1": {
                'items': {
                    "files": {
                        "/tmp/foo": {
                            'content': "one",
                        },
                    },
                },
            },
            "bundle2": {
                'items': {
                    "files": {
                        "/tmp/foo": {
                            'content': "two",
                        },
                    },
                },
            },
            "bundle3": {
                'items': {
                    "files": {
                        "/tmp/secret": {
                            'content': "${repo.vault.password_for('test', key='404')}",
                            'content_type': 'mako',
                        },
                    },
                },
            },
        },
    )
    # whole node: the item with the missing Fault is skipped, the rest is diffed
    stdout, stderr, rcode = run("bw diff node1 node2", path=str(tmpdir))
    assert rcode == 0
    assert b"file:/tmp/foo" in stdout
    assert b"file:/tmp/secret" not in stdout
    assert b"file:/tmp/secret  (Fault unavailable)" in stderr
    assert b"Traceback" not in stderr

    # single item: nothing to diff without the Fault
    stdout, stderr, rcode = run("bw diff -i file:/tmp/secret -- node1 node2", path=str(tmpdir))
    assert rcode == 1
    assert b"file:/tmp/secret  (Fault unavailable)" in stderr
    assert b"Traceback" not in stderr


def test_fault_unavailable_attribute(tmpdir):
    make_repo(
        tmpdir,
        nodes={
            "node1": {'bundles': ["bundle1"]},
            "node2": {'bundles': ["bundle1"]},
        },
        bundles={"bundle1": {}},
    )
    with open(join(str(tmpdir), "bundles", "bundle1", "items.py"), 'w') as f:
        f.write("""
files = {
    "/tmp/secret": {
        'content': repo.vault.password_for('test', key='404'),
    },
}
""")
    stdout, stderr, rcode = run("bw diff -i file:/tmp/secret -- node1 node2", path=str(tmpdir))
    assert rcode == 1
    assert b"file:/tmp/secret  (Fault unavailable)" in stderr
    assert b"Traceback" not in stderr


def test_delete_items(tmpdir):
    make_repo(
        tmpdir,
        nodes={
            "node1": {'bundles': ["bundle1"]},
            "node2": {'bundles': ["bundle1"]},
        },
        bundles={
            "bundle1": {
                'items': {
                    "files": {
                        "/tmp/gone": {
                            'delete': True,
                        },
                    },
                },
            },
        },
    )
    stdout, stderr, rcode = run("bw diff -i file:/tmp/gone -- node1 node2", path=str(tmpdir))
    assert rcode == 0
    assert stderr == b""


def test_metadata_fault_unavailable(tmpdir):
    make_repo(tmpdir)
    with open(join(str(tmpdir), "nodes.py"), 'w') as f:
        f.write("""
nodes = {
    'node1': {
        'metadata': {'secret': vault.password_for("testing", key="404"), 'foo': 1},
    },
    'node2': {
        'metadata': {'secret': vault.password_for("testing", key="404"), 'foo': 2},
    },
}
""")
    stdout, stderr, rcode = run("bw diff -m node1 node2", path=str(tmpdir))
    assert rcode == 0
    assert b"Traceback" not in stderr
    assert b"Fault unavailable" in stderr
    # both sides are rendered unresolved, so the shared Fault is not a difference
    assert not [
        line for line in stdout.splitlines()
        if line.startswith((b"-", b"+")) and b"secret" in line
    ]
    assert b'-    "foo": 1' in stdout
    assert b'+    "foo": 2' in stdout


def _git_repo_with_branch(tmpdir, branch_edit):
    """
    Turns tmpdir into a git repo on branch 'main' and creates a branch
    'other' with the given edit applied (a callable taking tmpdir).
    """
    git = "git -c user.email=t@example.com -c user.name=t -c commit.gpgsign=false "
    run(git + "init -q -b main", path=str(tmpdir))
    run(git + "add -A && " + git + "commit -q -m base", path=str(tmpdir))
    run(git + "checkout -q -b other", path=str(tmpdir))
    branch_edit(tmpdir)
    run(git + "add -A && " + git + "commit -q -m other", path=str(tmpdir))
    run(git + "checkout -q main", path=str(tmpdir))


def test_branch_metadata_fault_unavailable(tmpdir):
    make_repo(
        tmpdir,
        nodes={
            "node1": {'metadata': {'secret': "plain"}},
            "node2": {'metadata': {'secret': "plain"}},
        },
    )

    def edit(tmpdir):
        with open(join(str(tmpdir), "nodes.py"), 'w') as f:
            f.write("""
nodes = {
    'node1': {'metadata': {'secret': vault.password_for("testing", key="404")}},
    'node2': {'metadata': {'secret': vault.password_for("testing", key="404")}},
}
""")
    _git_repo_with_branch(tmpdir, edit)

    for command in ("bw diff -m -b other node1", "bw diff -m -b other node1 node2"):
        stdout, stderr, rcode = run(command, path=str(tmpdir))
        assert rcode == 0, command
        assert b"Traceback" not in stderr, command
        assert b"Fault unavailable" in stderr, command
        branch, _, _ = run("git rev-parse --abbrev-ref HEAD", path=str(tmpdir))
        assert branch.strip() == b"main", command


def test_branch_item_fault_unavailable(tmpdir):
    make_repo(
        tmpdir,
        nodes={"node1": {'bundles': ["bundle1"]}},
        bundles={
            "bundle1": {
                'items': {
                    "files": {
                        "/tmp/secret": {
                            'content': "plain",
                        },
                    },
                },
            },
        },
    )

    def edit(tmpdir):
        with open(join(str(tmpdir), "bundles", "bundle1", "items.py"), 'w') as f:
            f.write("""
files = {
    "/tmp/secret": {
        'content': "${repo.vault.password_for('test', key='404')}",
        'content_type': 'mako',
    },
}
""")
    _git_repo_with_branch(tmpdir, edit)

    stdout, stderr, rcode = run("bw diff -i file:/tmp/secret -b other node1", path=str(tmpdir))
    assert rcode == 1
    assert b"Traceback" not in stderr
    assert b"file:/tmp/secret  (Fault unavailable)" in stderr
    # the available side must not be presented as an added/removed item
    assert b"plain" not in stdout
    branch, _, _ = run("git rev-parse --abbrev-ref HEAD", path=str(tmpdir))
    assert branch.strip() == b"main"
