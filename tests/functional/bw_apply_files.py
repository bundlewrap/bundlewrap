# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from os.path import join

from bundlewrap.cmdline import main
from bundlewrap.utils.testing import make_repo


def test_empty(tmpdir):
    make_repo(
        tmpdir,
        bundles={
            "test": {
                'files': {
                    join(str(tmpdir), "foo.bin"): {
                        'content_type': 'binary',
                        'content': "ö".encode('latin-1'),
                    },
                },
            },
        },
        nodes={
            "localhost": {
                'bundles': ["test"],
            },
        },
    )
    main("apply", "localhost", path=str(tmpdir))
    with open(join(str(tmpdir), "foo.bin"), 'rb') as f:
        content = f.read()
    assert content.decode('latin-1') == "ö"
