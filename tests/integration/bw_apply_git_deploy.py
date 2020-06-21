from os.path import exists, join

from bundlewrap.utils.testing import host_os, make_repo, run


def test_deploy_from_url(tmpdir):
    make_repo(
        tmpdir,
        bundles={
            "test": {
                'git_deploy': {
                    join(str(tmpdir), "git_deployed_bw"): {
                        'needs': {"directory:" + join(str(tmpdir), "git_deployed_bw")},
                        'repo': "https://github.com/bundlewrap/bundlewrap.git",
                        'rev': "master",
                    },
                },
                'directories': {
                    join(str(tmpdir), "git_deployed_bw"): {},
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

    assert not exists(join(str(tmpdir), "git_deployed_bw", "LICENSE"))
    stdout, stderr, rcode = run("bw apply localhost", path=str(tmpdir))
    assert rcode == 0
    assert exists(join(str(tmpdir), "git_deployed_bw", "LICENSE"))
    assert not exists(join(str(tmpdir), "git_deployed_bw", ".git"))
