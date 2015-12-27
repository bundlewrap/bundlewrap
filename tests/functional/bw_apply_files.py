# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from base64 import b64encode
from os.path import join

from bundlewrap.cmdline import main
from bundlewrap.utils.testing import host_os, make_repo


def test_binary_inline_content(tmpdir):
    make_repo(
        tmpdir,
        bundles={
            "test": {
                'files': {
                    join(str(tmpdir), "foo.bin"): {
                        'content_type': 'base64',
                        'content': b64encode("ö".encode('latin-1')),
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
    main("apply", "localhost", path=str(tmpdir))
    with open(join(str(tmpdir), "foo.bin"), 'rb') as f:
        content = f.read()
    assert content.decode('latin-1') == "ö"
