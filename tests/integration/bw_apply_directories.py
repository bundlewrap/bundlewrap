from os import mkdir
from os.path import exists, join

from bundlewrap.utils.testing import host_os, make_repo, run


def test_purge(tmpdir):
    make_repo(
        tmpdir,
        bundles={
            "test": {
                'items': {
                    'files': {
                        join(str(tmpdir), "purgedir", "managed_file"): {
                            'content': "content",
                        },
                        join(str(tmpdir), "purgedir", "subdir1", "managed_file"): {
                            'content': "content",
                        },
                    },
                    'directories': {
                        join(str(tmpdir), "purgedir"): {
                            'purge': True,
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

    mkdir(join(str(tmpdir), "purgedir"))
    mkdir(join(str(tmpdir), "purgedir", "subdir2"))
    mkdir(join(str(tmpdir), "purgedir", "subdir3"))

    with open(join(str(tmpdir), "purgedir", "unmanaged_file"), 'w') as f:
        f.write("content")
    with open(join(str(tmpdir), "purgedir", "subdir3", "unmanaged_file"), 'w') as f:
        f.write("content")

    run("bw apply localhost", path=str(tmpdir))

    assert not exists(join(str(tmpdir), "purgedir", "unmanaged_file"))
    assert not exists(join(str(tmpdir), "purgedir", "subdir3", "unmanaged_file"))
    assert not exists(join(str(tmpdir), "purgedir", "subdir2"))
    assert exists(join(str(tmpdir), "purgedir", "subdir1", "managed_file"))
    assert exists(join(str(tmpdir), "purgedir", "managed_file"))


def test_purge_special_chars(tmpdir):
    make_repo(
        tmpdir,
        bundles={
            "test": {
                'items': {
                    'files': {
                        join(str(tmpdir), "purgedir", "mänäged_file"): {
                            'content': "content",
                        },
                        join(str(tmpdir), "purgedir", "managed_`id`_file"): {
                            'content': "content",
                        },
                    },
                    'directories': {
                        join(str(tmpdir), "purgedir"): {
                            'purge': True,
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

    mkdir(join(str(tmpdir), "purgedir"))

    with open(join(str(tmpdir), "purgedir", "unmänäged_file"), 'w') as f:
        f.write("content")
    with open(join(str(tmpdir), "purgedir", "unmanaged_`uname`_file"), 'w') as f:
        f.write("content")
    with open(join(str(tmpdir), "purgedir", "unmanaged_:'_file"), 'w') as f:
        f.write("content")

    run("bw apply localhost", path=str(tmpdir))

    assert not exists(join(str(tmpdir), "purgedir", "unmänäged_file"))
    assert not exists(join(str(tmpdir), "purgedir", "unmanaged_`uname`_file"))
    assert not exists(join(str(tmpdir), "purgedir", "unmanaged_:'_file"))
    assert exists(join(str(tmpdir), "purgedir", "mänäged_file"))
    assert exists(join(str(tmpdir), "purgedir", "managed_`id`_file"))
