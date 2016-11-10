from os.path import exists, join

from bundlewrap.utils.testing import host_os, make_repo, run


def test_apply(tmpdir):
    make_repo(
        tmpdir,
        bundles={
            "bundle1": {
                'files': {
                    join(str(tmpdir), "test"): {
                        'content': "test",
                    },
                },
            },
        },
        groups={
            "adhoc-localhost": {
                'bundles': ["bundle1"],
                'member_patterns': ["localhost"],
                'os': host_os(),
            },
        },
    )

    assert not exists(join(str(tmpdir), "test"))
    stdout, stderr, rcode = run("bw -A apply localhost", path=str(tmpdir))
    assert rcode == 0
    assert exists(join(str(tmpdir), "test"))


def test_apply_fail(tmpdir):
    make_repo(
        tmpdir,
        bundles={
            "bundle1": {
                'files': {
                    join(str(tmpdir), "test"): {
                        'content': "test",
                    },
                },
            },
        },
        groups={
            "adhoc-localhost": {
                'bundles': ["bundle1"],
                'member_patterns': ["localhost"],
                'os': host_os(),
            },
        },
    )

    assert not exists(join(str(tmpdir), "test"))
    stdout, stderr, rcode = run("bw apply localhost", path=str(tmpdir))
    assert rcode == 1
    assert not exists(join(str(tmpdir), "test"))
