from bundlewrap.utils.testing import host_os, make_repo, run


def test_empty_tags(tmpdir):
    make_repo(
        tmpdir,
        nodes={
            "localhost": {
                'bundles': ["bundle1"],
                'os': host_os(),
            },
        },
        bundles={
            "bundle1": {
                'attrs': {
                    'tags': {
                        "empty": {
                            'needs': {"action:early"},
                        },
                    },
                },
                'items': {
                    'actions': {
                        "early": {
                            'command': "true",
                        },
                        "late": {
                            'command': "true",
                            'needs': {"tag:empty"},
                        },
                    },
                },
            },
        },
    )
    stdout, stderr, rcode = run("bw apply localhost", path=str(tmpdir))
    assert rcode == 0


def test_empty_tag_loop(tmpdir):
    make_repo(
        tmpdir,
        nodes={
            "localhost": {
                'bundles': ["bundle1"],
                'os': host_os(),
            },
        },
        bundles={
            "bundle1": {
                'attrs': {
                    'tags': {
                        "1": {
                            'needs': {"tag:2"},
                        },
                        "2": {
                            'tags': {"3"},
                        },
                        "3": {
                            'needs': {"tag:1"},
                        },
                    },
                },
                'items': {
                    'actions': {
                        "early": {
                            'command': "true",
                        },
                    },
                },
            },
        },
    )
    stdout, stderr, rcode = run("bw apply localhost", path=str(tmpdir))
    assert rcode == 1
