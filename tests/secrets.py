# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from base64 import b64decode
from os.path import join

from bundlewrap.utils.testing import make_repo, run


def test_generate_password(tmpdir):
    make_repo(tmpdir)
    stdout, stderr, rcode = run("bw debug -c 'print(repo.vault.password_for(\"test\"))'", path=str(tmpdir))
    assert stdout == b"Q4WeYdfKaSOOPF8pz13z7yRbjJ6HD7ZB\n"
    assert stderr == b""
    assert rcode == 0


def test_encrypt(tmpdir):
    make_repo(tmpdir)

    stdout, stderr, rcode = run("bw debug -c 'print(repo.vault.encrypt(\"test\"))'", path=str(tmpdir))
    assert stderr == b""
    assert rcode == 0

    stdout, stderr, rcode = run("bw debug -c 'print(repo.vault.decrypt(\"{}\"))'".format(stdout.decode('utf-8').strip()), path=str(tmpdir))
    assert stdout == b"test\n"
    assert stderr == b""
    assert rcode == 0


def test_encrypt_file(tmpdir):
    make_repo(tmpdir)

    source_file = join(str(tmpdir), "data", "source")
    with open(source_file, 'w') as f:
        f.write("ohai")

    stdout, stderr, rcode = run(
        "bw debug -c 'repo.vault.encrypt_file(\"{}\", \"{}\")'".format(
            source_file,
            "encrypted",
        ),
        path=str(tmpdir),
    )
    assert stderr == b""
    assert rcode == 0

    stdout, stderr, rcode = run(
        "bw debug -c 'print(repo.vault.decrypt_file(\"{}\"))'".format(
            "encrypted",
        ),
        path=str(tmpdir),
    )
    assert stdout == b"ohai\n"
    assert stderr == b""
    assert rcode == 0


def test_encrypt_file_base64(tmpdir):
    make_repo(tmpdir)

    source_file = join(str(tmpdir), "data", "source")
    with open(source_file, 'wb') as f:
        f.write("öhai".encode('latin-1'))

    stdout, stderr, rcode = run(
        "bw debug -c 'repo.vault.encrypt_file(\"{}\", \"{}\")'".format(
            source_file,
            "encrypted",
        ),
        path=str(tmpdir),
    )
    assert stderr == b""
    assert rcode == 0

    stdout, stderr, rcode = run(
        "bw debug -c 'print(repo.vault.decrypt_file_as_base64(\"{}\"))'".format(
            "encrypted",
        ),
        path=str(tmpdir),
    )
    assert b64decode(stdout.decode('utf-8')) == "öhai".encode('latin-1')
    assert stderr == b""
    assert rcode == 0


def test_no_key(tmpdir):
    make_repo(tmpdir)
    run("rm .secrets.cfg", path=str(tmpdir))

    stdout, stderr, rcode = run("bw debug -c 'repo.vault.password_for(\"test\")'", path=str(tmpdir))
    assert rcode == 0

    stdout, stderr, rcode = run("bw debug -c 'repo.vault.password_for(\"test\").value'", path=str(tmpdir))
    assert rcode == 1

    stdout, stderr, rcode = run("bw debug -c 'str(repo.vault.password_for(\"test\"))'", path=str(tmpdir))
    assert rcode == 1
