from re import search

from bundlewrap.utils.testing import host_os, make_repo, run


def get_lock_id(output):
    return search(r"locked with ID (\w+) ", output).groups()[0]


def test_add_lock_apply_remove(tmpdir):
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
                'items': {
                    'files': {
                        "/tmp/bw_test_lock_add": {
                            'content': "foo",
                        },
                    },
                },
            },
        },
    )
    run("sudo rm -f /tmp/bw_test_lock_add")
    stdout, stderr, rcode = run("BW_IDENTITY=jdoe bw lock add -c höhöhö -e 1m -i file:/tmp/bw_test_lock_add -- localhost", path=str(tmpdir))
    assert rcode == 0
    lock_id = get_lock_id(stdout.decode('utf-8'))
    assert len(lock_id) == 4
    stdout, stderr, rcode = run("bw -d apply localhost", path=str(tmpdir))
    assert rcode == 0
    stdout, stderr, rcode = run("cat /tmp/bw_test_lock_add", path=str(tmpdir))
    assert rcode != 0
    stdout, stderr, rcode = run("bw lock remove localhost {}".format(lock_id), path=str(tmpdir))
    assert rcode == 0
