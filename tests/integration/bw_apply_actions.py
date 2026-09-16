from bundlewrap.utils.testing import host_os, make_repo, run
from os.path import join


def test_action_success(tmpdir):
    make_repo(
        tmpdir,
        bundles={
            "test": {
                'items': {
                    'actions': {
                        "success": {
                            'command': "true",
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
    stdout, stderr, rcode = run("bw apply localhost", path=str(tmpdir))
    assert rcode == 0


def test_action_fail(tmpdir):
    make_repo(
        tmpdir,
        bundles={
            "test": {
                'items': {
                    'actions': {
                        "failure": {
                            'command': "false",
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
    stdout, stderr, rcode = run("bw apply localhost", path=str(tmpdir))
    assert rcode == 1


def test_action_pipe_binary(tmpdir):
    make_repo(
        tmpdir,
        bundles={
            "test": {
                'items': {
                    'actions': {
                        "pipe": {
                            'command': "cat",
                            'data_stdin': b"hello\000world",
                            'expected_stdout': b"hello\000world",
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
    stdout, stderr, rcode = run("bw apply localhost", path=str(tmpdir))
    assert rcode == 0


def test_action_pipe_utf8(tmpdir):
    make_repo(
        tmpdir,
        bundles={
            "test": {
                'items': {
                    'actions': {
                        "pipe": {
                            'command': "cat",
                            'data_stdin': "hello 🐧\n",
                            'expected_stdout': "hello 🐧\n",
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
    stdout, stderr, rcode = run("bw apply localhost", path=str(tmpdir))
    assert rcode == 0


def test_action_return_codes(tmpdir):
    make_repo(
        tmpdir,
        bundles={
            "test": {
                'items': {
                    'actions': {
                        "single-code": {
                            'command': "true",
                            'expected_return_code': 0,
                        },
                        "multi-code-list": {
                            'command': "false",
                            'expected_return_code': [1],
                        },
                        "multi-code-tuple": {
                            'command': "false",
                            'expected_return_code': (1,),
                        },
                        "multi-code-set": {
                            'command': "false",
                            'expected_return_code': {1},
                        }
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
    stdout, stderr, rcode = run("bw apply localhost", path=str(tmpdir))
    assert rcode == 0


def test_action_ok_when(tmpdir):
    make_repo(
        tmpdir,
        bundles={
            "test": {
                'items': {
                    'actions': {
                        "action1": {
                            'command': "echo 1 >> {}".format(join(str(tmpdir), "file")),
                            'ok_when': 'true',
                        },
                        "action2": {
                            'command': "echo 2 >> {}".format(join(str(tmpdir), "file")),
							'ok_when': 'false',
                            'needs': ["action:action1"],
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

    stdout, stderr, rcode = run("bw apply localhost", path=str(tmpdir))
    assert rcode == 0

    with open(join(str(tmpdir), "file")) as f:
        content = f.read()
    assert content == "2\n"


def test_action_ok_when2(tmpdir):
    make_repo(
        tmpdir,
        bundles={
            "test": {
                'items': {
                    'actions': {
                        "action1": {
                            'command': "false",
							'ok_when': 'false',
                        },
                        "action2": {
                            'command': "echo 2 >> {}".format(join(str(tmpdir), "file")),
                            'needs': ["action:action1"],
                        },
						"action3": {
                            'command': "echo 3 >> {}".format(join(str(tmpdir), "file")),
                            'after': ["action:action2"],
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

    stdout, stderr, rcode = run("bw apply localhost", path=str(tmpdir))
    assert rcode == 1

    with open(join(str(tmpdir), "file")) as f:
        content = f.read()
    assert content == "3\n"
