from os.path import exists, join

from bundlewrap.utils.testing import host_os, make_repo, run


def test_only_bundle_with_dep(tmpdir):
    make_repo(
        tmpdir,
        bundles={
            "test": {
                'items': {
                    'files': {
                        join(str(tmpdir), "foo"): {
                            'content_type': 'any',
                            'needs': ["file:" + join(str(tmpdir), "bar")],
                        },
                    },
                },
            },
            "test2": {
                'items': {
                    'files': {
                        join(str(tmpdir), "bar"): {
                            'content_type': 'any',
                        },
                        join(str(tmpdir), "baz"): {
                            'content_type': 'any',
                        },
                    },
                },
            },
        },
        nodes={
            "localhost": {
                'bundles': ["test", "test2"],
                'os': host_os(),
            },
        },
    )

    run("bw apply -o bundle:test -- localhost", path=str(tmpdir))
    assert exists(join(str(tmpdir), "foo"))
    assert exists(join(str(tmpdir), "bar"))
    assert not exists(join(str(tmpdir), "baz"))
