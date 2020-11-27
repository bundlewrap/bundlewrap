from json import loads
from os import environ

from bundlewrap.utils.testing import host_os, make_repo, run


if environ.get('TRAVIS') == "true":
    def test_create(tmpdir):
        make_repo(
            tmpdir,
            bundles={
                "test": {
                    'items': {
                        'postgres_dbs': {
                            "bw-test1": {
                                'owner': "bw-test1",
                            },
                        },
                        'postgres_roles': {
                            "bw-test1": {
                                'superuser': True,
                                'password': 'potato',
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

        stdout, stderr, rcode = run("bw items --state localhost postgres_db:bw-test1", path=str(tmpdir))
        assert rcode == 0
        assert loads(stdout.decode()) == {'owner': "bw-test1"}

        stdout, stderr, rcode = run("bw items --state localhost postgres_role:bw-test1", path=str(tmpdir))
        assert rcode == 0
        assert loads(stdout.decode()) == {
            'can_login': True,
            'password_hash': "md5ecba3aec62c5aabf6480de6352182004",
            'superuser': True,
        }

        stdout, stderr, rcode = run("dropdb bw-test1", path=str(tmpdir))
        assert rcode == 0
        stdout, stderr, rcode = run("dropuser bw-test1", path=str(tmpdir))
        assert rcode == 0
