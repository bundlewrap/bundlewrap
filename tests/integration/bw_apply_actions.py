from bundlewrap.utils.testing import host_os, make_repo, run


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
    run("bw apply localhost", path=str(tmpdir))


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
    run("bw apply localhost", path=str(tmpdir))


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
    run("bw apply localhost", path=str(tmpdir))


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
    run("bw apply localhost", path=str(tmpdir))


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
    run("bw apply localhost", path=str(tmpdir))
