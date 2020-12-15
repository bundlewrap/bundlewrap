from os.path import exists, join

from bundlewrap.utils.testing import host_os, make_repo, run


def test_precedes(tmpdir):
    make_repo(
        tmpdir,
        bundles={
            "test": {
                'items': {
                    'files': {
                        join(str(tmpdir), "file"): {
                            'content': "1\n",
                            'triggered': True,
                            'precedes': ["tag:tag1"],
                        },
                    },
                    'actions': {
                        "action2": {
                            'command': "echo 2 >> {}".format(join(str(tmpdir), "file")),
                            'tags': ["tag1"],
                        },
                        "action3": {
                            'command': "echo 3 >> {}".format(join(str(tmpdir), "file")),
                            'tags': ["tag1"],
                            'needs': ["action:action2"],
                        },
                    },
                },
            },
        },
        nodes={
            "localhost": {
                'bundles': ["test"],
                'os': host_os(),
            },
        },
    )
    run("bw apply localhost", path=str(tmpdir))
    with open(join(str(tmpdir), "file")) as f:
        content = f.read()
    assert content == "1\n2\n3\n"


def test_precedes_unless(tmpdir):
    make_repo(
        tmpdir,
        bundles={
            "test": {
                'items': {
                    'files': {
                        join(str(tmpdir), "file"): {
                            'content': "1\n",
                            'triggered': True,
                            'precedes': ["tag:tag1"],
                        },
                    },
                    'actions': {
                        "action2": {
                            'command': "echo 2 >> {}".format(join(str(tmpdir), "file")),
                            'tags': ["tag1"],
                            'unless': 'true',
                        },
                        "action3": {
                            'command': "echo 3 >> {}".format(join(str(tmpdir), "file")),
                            'tags': ["tag1"],
                            'needs': ["action:action2"],
                        },
                    },
                },
            },
        },
        nodes={
            "localhost": {
                'bundles': ["test"],
                'os': host_os(),
            },
        },
    )
    run("bw apply localhost", path=str(tmpdir))
    with open(join(str(tmpdir), "file")) as f:
        content = f.read()
    assert content == "1\n3\n"


def test_precedes_unless2(tmpdir):
    make_repo(
        tmpdir,
        bundles={
            "test": {
                'items': {
                    'files': {
                        join(str(tmpdir), "file"): {
                            'content': "1\n",
                            'triggered': True,
                            'precedes': ["tag:tag1"],
                        },
                    },
                    'actions': {
                        "action2": {
                            'command': "echo 2 >> {}".format(join(str(tmpdir), "file")),
                            'tags': ["tag1"],
                            'unless': 'true',
                        },
                        "action3": {
                            'command': "echo 3 >> {}".format(join(str(tmpdir), "file")),
                            'tags': ["tag1"],
                            'needs': ["action:action2"],
                            'unless': 'true',
                        },
                    },
                },
            },
        },
        nodes={
            "localhost": {
                'bundles': ["test"],
                'os': host_os(),
            },
        },
    )
    run("bw apply localhost", path=str(tmpdir))
    assert not exists(join(str(tmpdir), "file"))


def test_precedes_unless3(tmpdir):
    make_repo(
        tmpdir,
        bundles={
            "test": {
                'items': {
                    'files': {
                        join(str(tmpdir), "file"): {
                            'content': "1\n",
                            'triggered': True,
                            'precedes': ["tag:tag1"],
                            'unless': 'true',
                        },
                    },
                    'actions': {
                        "action2": {
                            'command': "echo 2 >> {}".format(join(str(tmpdir), "file")),
                            'tags': ["tag1"],
                        },
                        "action3": {
                            'command': "echo 3 >> {}".format(join(str(tmpdir), "file")),
                            'tags': ["tag1"],
                            'needs': ["action:action2"],
                        },
                    },
                },
            },
        },
        nodes={
            "localhost": {
                'bundles': ["test"],
                'os': host_os(),
            },
        },
    )
    run("bw apply localhost", path=str(tmpdir))
    with open(join(str(tmpdir), "file")) as f:
        content = f.read()
    assert content == "2\n3\n"


def test_precedes_unless4(tmpdir):
    make_repo(
        tmpdir,
        bundles={
            "test": {
                'items': {
                    'files': {
                        join(str(tmpdir), "file"): {
                            'content': "1\n",
                            'triggered': True,
                            'precedes': ["action:action3"],
                        },
                    },
                    'actions': {
                        "action2": {
                            'command': "false",
                            'needs': ["file:{}".format(join(str(tmpdir), "file"))],
                        },
                        "action3": {
                            'command': "echo 3 >> {}".format(join(str(tmpdir), "file")),
                            'needs': ["action:action2"],
                        },
                    },
                },
            },
        },
        nodes={
            "localhost": {
                'bundles': ["test"],
                'os': host_os(),
            },
        },
    )
    run("bw apply localhost", path=str(tmpdir))
    with open(join(str(tmpdir), "file")) as f:
        content = f.read()
    assert content == "1\n"


def test_precedes_action(tmpdir):
    make_repo(
        tmpdir,
        bundles={
            "test": {
                'items': {
                    'actions': {
                        "action1": {
                            'command': "echo 1 > {}".format(join(str(tmpdir), "file")),
                            'precedes': ["action:action2"],
                            'triggered': True,
                        },
                        "action2": {
                            'command': "echo 2 >> {}".format(join(str(tmpdir), "file")),
                        },
                    },
                },
            },
        },
        nodes={
            "localhost": {
                'bundles': ["test"],
                'os': host_os(),
            },
        },
    )
    run("bw apply localhost", path=str(tmpdir))
    with open(join(str(tmpdir), "file")) as f:
        content = f.read()
    assert content == "1\n2\n"
