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
