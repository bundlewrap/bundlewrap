# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from base64 import b64decode
from os.path import join

from bundlewrap.utils.testing import make_repo, run


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


def test_format_password(tmpdir):
    make_repo(tmpdir)

    stdout, stderr, rcode = run("bw debug -c 'print(repo.vault.format(\"format: {}\", repo.vault.password_for(\"testing\")))'", path=str(tmpdir))
    assert stdout == b"format: faCTT76kagtDuZE5wnoiD1CxhGKmbgiX\n"
    assert stderr == b""
    assert rcode == 0


def test_human_password(tmpdir):
    make_repo(tmpdir)

    stdout, stderr, rcode = run("bw debug -c 'print(repo.vault.human_password_for(\"hello world\"))'", path=str(tmpdir))
    assert stdout == b"Xaint-Heep-Pier-Tikl-76\n"
    assert stderr == b""
    assert rcode == 0


def test_human_password_digits(tmpdir):
    make_repo(tmpdir)

    stdout, stderr, rcode = run("bw debug -c 'print(repo.vault.human_password_for(\"hello world\", digits=4))'", path=str(tmpdir))
    assert stdout == b"Xaint-Heep-Pier-Tikl-7608\n"
    assert stderr == b""
    assert rcode == 0


def test_human_password_per_word(tmpdir):
    make_repo(tmpdir)

    stdout, stderr, rcode = run("bw debug -c 'print(repo.vault.human_password_for(\"hello world\", per_word=1))'", path=str(tmpdir))
    assert stdout == b"X-D-F-H-42\n"
    assert stderr == b""
    assert rcode == 0


def test_human_password_words(tmpdir):
    make_repo(tmpdir)

    stdout, stderr, rcode = run("bw debug -c 'print(repo.vault.human_password_for(\"hello world\", words=2))'", path=str(tmpdir))
    assert stdout == b"Xaint-Heep-13\n"
    assert stderr == b""
    assert rcode == 0
