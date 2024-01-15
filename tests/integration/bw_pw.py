from os.path import join

from bundlewrap.utils.testing import make_repo, run


def test_encrypt(tmpdir):
    make_repo(tmpdir)

    stdout, stderr, rcode = run("bw pw -e test", path=str(tmpdir))
    assert stderr == b""
    assert rcode == 0

    stdout, stderr, rcode = run("bw pw -d '{}'".format(stdout.decode('utf-8').strip()), path=str(tmpdir))
    assert stdout == b"test\n"
    assert stderr == b""
    assert rcode == 0


def test_encrypt_different_key_autodetect(tmpdir):
    make_repo(tmpdir)

    stdout, stderr, rcode = run("bw pw -e -k generate test", path=str(tmpdir))
    assert stderr == b""
    assert rcode == 0
    print(stdout)

    stdout, stderr, rcode = run("bw pw -d '{}'".format(stdout.decode('utf-8').strip()), path=str(tmpdir))
    assert stdout == b"test\n"
    assert stderr == b""
    assert rcode == 0


def test_encrypt_file(tmpdir):
    make_repo(tmpdir)

    source_file = join(str(tmpdir), "data", "source")
    with open(source_file, 'w') as f:
        f.write("ohai")

    stdout, stderr, rcode = run(
        f"bw pw -e -f encrypted \"{source_file}\"",
        path=str(tmpdir),
    )
    assert stderr == b""
    assert rcode == 0

    stdout, stderr, rcode = run(
        "bw pw -d -f decrypted encrypted",
        path=str(tmpdir),
    )
    assert stdout == b""
    assert stderr == b""
    assert rcode == 0
    with open(join(tmpdir, "data", "decrypted")) as f:
        assert f.read() == "ohai"


def test_encrypt_file_different_key_autodetect(tmpdir):
    make_repo(tmpdir)

    source_file = join(str(tmpdir), "data", "source")
    with open(source_file, 'w') as f:
        f.write("ohai")

    stdout, stderr, rcode = run(
        f"bw pw -e -f encrypted -k generate \"{source_file}\"",
        path=str(tmpdir),
    )
    assert stderr == b""
    assert rcode == 0

    stdout, stderr, rcode = run(
        "bw pw -d -f decrypted encrypted",
        path=str(tmpdir),
    )
    assert stdout == b""
    assert stderr == b""
    assert rcode == 0
    with open(join(tmpdir, "data", "decrypted")) as f:
        assert f.read() == "ohai"


def test_encrypt_file_binary(tmpdir):
    make_repo(tmpdir)

    source_file = join(str(tmpdir), "data", "source")
    with open(source_file, 'wb') as f:
        f.write(b"\000\001\002")

    stdout, stderr, rcode = run(
        f"bw pw -e -f encrypted \"{source_file}\"",
        path=str(tmpdir),
    )
    assert stderr == b""
    assert rcode == 0

    stdout, stderr, rcode = run(
        "bw pw -d -f decrypted encrypted",
        path=str(tmpdir),
    )
    assert stdout == b""
    assert stderr == b""
    assert rcode == 0
    with open(join(tmpdir, "data", "decrypted"), 'rb') as f:
        assert f.read() == b"\000\001\002"


def test_human_password(tmpdir):
    make_repo(tmpdir)

    stdout, stderr, rcode = run("bw pw -H \"hello world\"", path=str(tmpdir))
    assert stdout == b"Xaint-Heep-Pier-Tikl-76\n"
    assert stderr == b""
    assert rcode == 0


def test_random_bytes_as_base64(tmpdir):
    make_repo(tmpdir)

    stdout, stderr, rcode = run("bw pw -b foo", path=str(tmpdir))
    assert stdout == b"rt+Dgv0yA10DS3ux94mmtEg+isChTJvgkfklzmWkvyg=\n"
    assert stderr == b""
    assert rcode == 0


def test_random_bytes_as_base64_length(tmpdir):
    make_repo(tmpdir)

    stdout, stderr, rcode = run("bw pw -b -l 1 foo", path=str(tmpdir))
    assert stdout == b"rg==\n"
    assert stderr == b""
    assert rcode == 0
