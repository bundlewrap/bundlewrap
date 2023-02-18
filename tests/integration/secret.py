from base64 import b64decode
from os.path import join

from bundlewrap.utils.testing import make_repo, run


def test_b64encode_fault(tmpdir):
    make_repo(tmpdir)

    stdout, stderr, rcode = run("bw debug -c 'print(repo.vault.password_for(\"testing\").b64encode())'", path=str(tmpdir))
    assert stdout == b"ZmFDVFQ3NmthZ3REdVpFNXdub2lEMUN4aEdLbWJnaVg=\n"
    assert stderr == b""
    assert rcode == 0


def test_format_password(tmpdir):
    make_repo(tmpdir)

    stdout, stderr, rcode = run("bw debug -c 'print(repo.vault.password_for(\"testing\").format_into(\"format: {}\"))'", path=str(tmpdir))
    assert stdout == b"format: faCTT76kagtDuZE5wnoiD1CxhGKmbgiX\n"
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


def test_faults_equality_decrypt(tmpdir):
    make_repo(tmpdir)

    stdout, stderr, rcode = run("bw debug -c 'print(repo.vault.encrypt(\"foo\"))'", path=str(tmpdir))
    assert stderr == b""
    assert rcode == 0
    enc_foo = stdout.decode('utf-8').strip()

    stdout, stderr, rcode = run(
        "bw debug -c 'print(repo.vault.encrypt(\"bar\"))'", path=str(tmpdir),
    )
    assert stderr == b""
    assert rcode == 0
    enc_bar = stdout.decode('utf-8').strip()

    stdout, stderr, rcode = run(
        "bw debug -c 'print(repo.vault.decrypt(\"{0}\") == repo.vault.decrypt(\"{0}\"))'".format(
            enc_foo,
        ),
        path=str(tmpdir),
    )
    assert stdout == b"True\n"
    assert stderr == b""
    assert rcode == 0

    stdout, stderr, rcode = run(
        "bw debug -c 'print(repo.vault.decrypt(\"{}\") == repo.vault.decrypt(\"{}\"))'".format(
            enc_foo, enc_bar,
        ),
        path=str(tmpdir),
    )
    assert stdout == b"False\n"
    assert stderr == b""
    assert rcode == 0


def test_faults_equality_decrypt_file(tmpdir):
    make_repo(tmpdir)

    source_file = join(str(tmpdir), "data", "source")
    with open(source_file, 'w') as f:
        f.write("foo")
    stdout, stderr, rcode = run(
        "bw debug -c 'repo.vault.encrypt_file(\"{}\", \"{}\")'".format(
            source_file,
            "enc_foo",
        ),
        path=str(tmpdir),
    )
    assert stderr == b""
    assert rcode == 0

    source_file = join(str(tmpdir), "data", "source")
    with open(source_file, 'w') as f:
        f.write("bar")
    stdout, stderr, rcode = run(
        "bw debug -c 'repo.vault.encrypt_file(\"{}\", \"{}\")'".format(
            source_file,
            "enc_bar",
        ),
        path=str(tmpdir),
    )
    assert stderr == b""
    assert rcode == 0

    stdout, stderr, rcode = run(
        "bw debug -c 'print(repo.vault.decrypt_file(\"{}\") == repo.vault.decrypt_file(\"{}\"))'".format(
            "enc_foo", "enc_foo",
        ),
        path=str(tmpdir),
    )
    assert stdout == b"True\n"
    assert stderr == b""
    assert rcode == 0

    stdout, stderr, rcode = run(
        "bw debug -c 'print(repo.vault.decrypt_file(\"{}\") == repo.vault.decrypt_file(\"{}\"))'".format(
            "enc_foo", "enc_bar",
        ),
        path=str(tmpdir),
    )
    assert stdout == b"False\n"
    assert stderr == b""
    assert rcode == 0


def test_faults_equality_decrypt_file_as_base64(tmpdir):
    make_repo(tmpdir)

    source_file = join(str(tmpdir), "data", "source")
    with open(source_file, 'w') as f:
        f.write("foo")
    stdout, stderr, rcode = run(
        "bw debug -c 'repo.vault.encrypt_file(\"{}\", \"{}\")'".format(
            source_file,
            "enc_foo",
        ),
        path=str(tmpdir),
    )
    assert stderr == b""
    assert rcode == 0

    source_file = join(str(tmpdir), "data", "source")
    with open(source_file, 'w') as f:
        f.write("bar")
    stdout, stderr, rcode = run(
        "bw debug -c 'repo.vault.encrypt_file(\"{}\", \"{}\")'".format(
            source_file,
            "enc_bar",
        ),
        path=str(tmpdir),
    )
    assert stderr == b""
    assert rcode == 0

    stdout, stderr, rcode = run(
        "bw debug -c 'print(repo.vault.decrypt_file_as_base64(\"{}\") == repo.vault.decrypt_file_as_base64(\"{}\"))'".format(
            "enc_foo", "enc_foo",
        ),
        path=str(tmpdir),
    )
    assert stdout == b"True\n"
    assert stderr == b""
    assert rcode == 0

    stdout, stderr, rcode = run(
        "bw debug -c 'print(repo.vault.decrypt_file_as_base64(\"{}\") == repo.vault.decrypt_file_as_base64(\"{}\"))'".format(
            "enc_foo", "enc_bar",
        ),
        path=str(tmpdir),
    )
    assert stdout == b"False\n"
    assert stderr == b""
    assert rcode == 0


def test_faults_equality_decrypt_file_mixed(tmpdir):
    make_repo(tmpdir)

    source_file = join(str(tmpdir), "data", "source")
    with open(source_file, 'w') as f:
        f.write("foo")
    stdout, stderr, rcode = run(
        "bw debug -c 'repo.vault.encrypt_file(\"{}\", \"{}\")'".format(
            source_file,
            "enc_foo",
        ),
        path=str(tmpdir),
    )
    assert stderr == b""
    assert rcode == 0

    stdout, stderr, rcode = run(
        "bw debug -c 'print(repo.vault.decrypt_file_as_base64(\"{}\") == repo.vault.decrypt_file(\"{}\"))'".format(
            "enc_foo", "enc_foo",
        ),
        path=str(tmpdir),
    )
    assert stdout == b"False\n"
    assert stderr == b""
    assert rcode == 0


def test_faults_equality_human_password_for(tmpdir):
    make_repo(tmpdir)

    stdout, stderr, rcode = run(
        "bw debug -c 'print(repo.vault.human_password_for(\"a\") == repo.vault.human_password_for(\"a\"))'",
        path=str(tmpdir),
    )
    assert stdout == b"True\n"
    assert stderr == b""
    assert rcode == 0

    stdout, stderr, rcode = run(
        "bw debug -c 'print(repo.vault.human_password_for(\"a\") == repo.vault.human_password_for(\"b\"))'",
        path=str(tmpdir),
    )
    assert stdout == b"False\n"
    assert stderr == b""
    assert rcode == 0


def test_faults_equality_password_for(tmpdir):
    make_repo(tmpdir)

    stdout, stderr, rcode = run(
        "bw debug -c 'print(repo.vault.password_for(\"a\") == repo.vault.password_for(\"a\"))'",
        path=str(tmpdir),
    )
    assert stdout == b"True\n"
    assert stderr == b""
    assert rcode == 0

    stdout, stderr, rcode = run(
        "bw debug -c 'print(repo.vault.password_for(\"a\") == repo.vault.password_for(\"b\"))'",
        path=str(tmpdir),
    )
    assert stdout == b"False\n"
    assert stderr == b""
    assert rcode == 0


def test_faults_equality_password_for_mixed(tmpdir):
    make_repo(tmpdir)

    stdout, stderr, rcode = run(
        "bw debug -c 'print(repo.vault.password_for(\"a\") == repo.vault.human_password_for(\"a\"))'",
        path=str(tmpdir),
    )
    assert stdout == b"False\n"
    assert stderr == b""
    assert rcode == 0


def test_faults_equality_random_bytes_as_base64(tmpdir):
    make_repo(tmpdir)

    stdout, stderr, rcode = run(
        "bw debug -c 'print(repo.vault.random_bytes_as_base64_for(\"a\") == repo.vault.random_bytes_as_base64_for(\"a\"))'",
        path=str(tmpdir),
    )
    assert stdout == b"True\n"
    assert stderr == b""
    assert rcode == 0

    stdout, stderr, rcode = run(
        "bw debug -c 'print(repo.vault.random_bytes_as_base64_for(\"a\") == repo.vault.random_bytes_as_base64_for(\"b\"))'",
        path=str(tmpdir),
    )
    assert stdout == b"False\n"
    assert stderr == b""
    assert rcode == 0


def test_cmd(tmpdir):
    make_repo(tmpdir)

    stdout, stderr, rcode = run(
        "bw debug -c 'print(repo.vault.cmd(\"echo hi\"))'",
        path=str(tmpdir),
    )
    assert stdout == b"hi\n"
    assert stderr == b""
    assert rcode == 0


def test_cmd_binary_nostrip(tmpdir):
    make_repo(tmpdir)

    stdout, stderr, rcode = run(
        "bw debug -c 'print(repo.vault.cmd(\"echo hi\", as_text=False, strip=False))'",
        path=str(tmpdir),
    )
    assert stdout == b"b'hi\\n'\n"
    assert stderr == b""
    assert rcode == 0


def test_cmd_fail(tmpdir):
    make_repo(tmpdir)

    stdout, stderr, rcode = run(
        "bw debug -c 'print(repo.vault.cmd(\"false\"))'",
        path=str(tmpdir),
    )
    assert b"CalledProcessError" in stderr
    assert rcode == 1


def test_key_command(tmpdir):
    make_repo(tmpdir)

    stdout1, stderr1, rcode1 = run(
        "bw debug -c 'print(repo.vault.password_for(\"something\", key=\"encrypt\"))'",
        path=str(tmpdir),
    )
    assert rcode1 == 0

    stdout2, stderr2, rcode2 = run(
        "bw debug -c 'print(repo.vault.password_for(\"something\", key=\"command\"))'",
        path=str(tmpdir),
    )
    assert rcode2 == 0

    assert stdout1 == stdout2
