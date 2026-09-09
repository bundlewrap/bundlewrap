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


def _pw(tmpdir, args):
    stdout, stderr, rcode = run("bw pw " + args, path=str(tmpdir))
    assert stderr == b""
    assert rcode == 0
    return stdout.decode().strip()


def _pw_fails(tmpdir, args):
    stdout, stderr, rcode = run("bw pw " + args, path=str(tmpdir))
    assert rcode != 0


def _make_node_repo(tmpdir):
    # 'command' holds the same key material as 'encrypt'
    make_repo(
        tmpdir,
        groups={
            "group1": {"generate_key": "command", "encrypt_key": "generate"},
        },
        nodes={
            "plain": {},
            "keyed": {"groups": ["group1"]},
        },
    )


def test_node_password(tmpdir):
    _make_node_repo(tmpdir)
    assert _pw(tmpdir, "-n plain -p testing") == _pw(tmpdir, "-p testing")
    assert _pw(tmpdir, "-n keyed -p testing") == _pw(tmpdir, "-k encrypt -p testing")
    assert _pw(tmpdir, "-n keyed -p testing") != _pw(tmpdir, "-p testing")
    assert _pw(tmpdir, "-n keyed -k generate -p testing") == _pw(tmpdir, "-p testing")
    assert len(_pw(tmpdir, "-n keyed -p -l 8 testing")) == 8


def test_node_human(tmpdir):
    _make_node_repo(tmpdir)
    assert _pw(tmpdir, "-n plain -H testing") == _pw(tmpdir, "-H testing")
    assert _pw(tmpdir, "-n keyed -H testing") == _pw(tmpdir, "-k encrypt -H testing")
    assert _pw(tmpdir, "-n keyed -H testing") != _pw(tmpdir, "-H testing")
    assert _pw(tmpdir, "-n keyed -k generate -H testing") == _pw(tmpdir, "-H testing")


def test_node_bytes(tmpdir):
    _make_node_repo(tmpdir)
    assert _pw(tmpdir, "-n plain -b testing") == _pw(tmpdir, "-b testing")
    assert _pw(tmpdir, "-n keyed -b testing") == _pw(tmpdir, "-k encrypt -b testing")
    assert _pw(tmpdir, "-n keyed -b testing") != _pw(tmpdir, "-b testing")
    assert _pw(tmpdir, "-n keyed -k generate -b testing") == _pw(tmpdir, "-b testing")
    assert _pw(tmpdir, "-n keyed -b -l 1 foo") == _pw(tmpdir, "-k encrypt -b -l 1 foo")


def test_node_encrypt(tmpdir):
    _make_node_repo(tmpdir)
    cryptotext = _pw(tmpdir, "-n keyed -e test")
    assert cryptotext.startswith("generate$")
    assert _pw(tmpdir, "-n plain -e test").startswith("encrypt$")
    assert _pw(tmpdir, "-n keyed -k encrypt -e test").startswith("encrypt$")
    # the key prefix is honored with and without -n
    assert _pw(tmpdir, "-d '{}'".format(cryptotext)) == "test"
    assert _pw(tmpdir, "-n plain -d '{}'".format(cryptotext)) == "test"


def test_node_decrypt_without_prefix(tmpdir):
    _make_node_repo(tmpdir)
    # without prefix, decryption uses 'encrypt' with and without -n
    raw = _pw(tmpdir, "-n keyed -e test").split("$", 1)[1]
    assert _pw(tmpdir, "-k generate -d '{}'".format(raw)) == "test"
    assert _pw(tmpdir, "-n keyed -k generate -d '{}'".format(raw)) == "test"
    _pw_fails(tmpdir, "-n keyed -d '{}'".format(raw))
    raw_default = _pw(tmpdir, "-e test").split("$", 1)[1]
    assert _pw(tmpdir, "-n keyed -d '{}'".format(raw_default)) == "test"


def test_decrypt_prefix_wins_over_key_option(tmpdir):
    _make_node_repo(tmpdir)
    cryptotext = _pw(tmpdir, "-k generate -e test")
    assert cryptotext.startswith("generate$")
    assert _pw(tmpdir, "-d -k encrypt '{}'".format(cryptotext)) == "test"
    assert _pw(tmpdir, "-n plain -d -k encrypt '{}'".format(cryptotext)) == "test"


def test_node_encrypt_file(tmpdir):
    _make_node_repo(tmpdir)
    source_file = join(str(tmpdir), "data", "source")
    with open(source_file, 'w') as f:
        f.write("ohai")

    assert _pw(tmpdir, "-n keyed -e -f encrypted \"{}\"".format(source_file)) == ""
    with open(join(tmpdir, "data", "encrypted"), 'rb') as f:
        assert f.read().startswith(b"generate$")

    assert _pw(tmpdir, "-n keyed -d -f decrypted encrypted") == ""
    with open(join(tmpdir, "data", "decrypted")) as f:
        assert f.read() == "ohai"

    assert _pw(tmpdir, "-d -f decrypted2 encrypted") == ""
    with open(join(tmpdir, "data", "decrypted2")) as f:
        assert f.read() == "ohai"


def test_node_unknown(tmpdir):
    _make_node_repo(tmpdir)
    _pw_fails(tmpdir, "-n nope -p testing")
    _pw_fails(tmpdir, "-n '' -p testing")
