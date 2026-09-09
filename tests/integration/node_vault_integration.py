from os import makedirs
from os.path import join

from bundlewrap.utils.testing import make_repo, run


def _attrs(tmpdir):
    stdout, stderr, rcode = run(
        "BW_TABLE_STYLE=grep bw nodes -a generate_key encrypt_key",
        path=str(tmpdir),
    )
    assert stderr == b""
    assert rcode == 0
    return {
        line.split("\t")[0]: line.split("\t")[1:]
        for line in stdout.decode().strip().split("\n")
    }


def test_key_attrs_from_groups(tmpdir):
    make_repo(
        tmpdir,
        groups={
            "group1": {"generate_key": "gen-group", "encrypt_key": "enc-group"},
        },
        nodes={
            "node1": {"groups": ["group1"]},
            "node2": {"groups": ["group1"], "generate_key": "gen-node"},
            "node3": {},
        },
    )
    rows = _attrs(tmpdir)
    assert rows["node1"] == ["gen-group", "enc-group"]
    assert rows["node2"] == ["gen-node", "enc-group"]
    assert rows["node3"] == ["None", "None"]


def test_key_attrs_in_toml(tmpdir):
    make_repo(tmpdir)
    makedirs(join(tmpdir, "groups"))
    with open(join(tmpdir, "groups", "group1.toml"), 'w') as f:
        f.write('members = ["node1"]\ngenerate_key = "gen-group"\nencrypt_key = "enc-group"\n')
    makedirs(join(tmpdir, "nodes"))
    with open(join(tmpdir, "nodes", "node1.toml"), 'w') as f:
        f.write("")
    with open(join(tmpdir, "nodes", "node2.toml"), 'w') as f:
        f.write('generate_key = "gen-node"\nencrypt_key = "enc-node"\n')
    rows = _attrs(tmpdir)
    assert rows["node1"] == ["gen-group", "enc-group"]
    assert rows["node2"] == ["gen-node", "enc-node"]


# In make_repo()'s .secrets.cfg, 'generate' and 'encrypt' differ while
# 'command' holds the same key material as 'encrypt'.

def _debug(tmpdir, node, expr):
    stdout, stderr, rcode = run(
        "bw debug -n {} -c 'print({})'".format(node, expr),
        path=str(tmpdir),
    )
    assert stderr == b""
    assert rcode == 0
    return stdout.decode().strip()


def _debug_fails(tmpdir, node, expr):
    stdout, stderr, rcode = run(
        "bw debug -n {} -c 'print({})'".format(node, expr),
        path=str(tmpdir),
    )
    assert rcode != 0


def _make_vault_repo(tmpdir):
    make_repo(
        tmpdir,
        groups={
            "group1": {"generate_key": "command", "encrypt_key": "generate"},
        },
        nodes={
            "plain": {},
            "keyed": {"groups": ["group1"]},
            "broken": {"generate_key": "nonexistent", "encrypt_key": "nonexistent"},
        },
    )


def test_node_vault_password_for(tmpdir):
    _make_vault_repo(tmpdir)
    assert _debug(tmpdir, "plain", 'node.vault.password_for("testing")') == \
        "faCTT76kagtDuZE5wnoiD1CxhGKmbgiX"
    assert _debug(tmpdir, "keyed", 'node.vault.password_for("testing")') == \
        _debug(tmpdir, "keyed", 'repo.vault.password_for("testing", key="encrypt")')
    assert _debug(tmpdir, "keyed", 'node.vault.password_for("testing")') != \
        "faCTT76kagtDuZE5wnoiD1CxhGKmbgiX"


def test_node_vault_human_password_for(tmpdir):
    _make_vault_repo(tmpdir)
    assert _debug(tmpdir, "plain", 'node.vault.human_password_for("hello world")') == \
        "Xaint-Heep-Pier-Tikl-76"
    assert _debug(tmpdir, "keyed", 'node.vault.human_password_for("hello world")') == \
        _debug(tmpdir, "keyed", 'repo.vault.human_password_for("hello world", key="encrypt")')
    assert _debug(tmpdir, "keyed", 'node.vault.human_password_for("hello world")') != \
        "Xaint-Heep-Pier-Tikl-76"


def test_node_vault_random_bytes_as_base64_for(tmpdir):
    _make_vault_repo(tmpdir)
    assert _debug(tmpdir, "plain", 'node.vault.random_bytes_as_base64_for("foo")') == \
        "rt+Dgv0yA10DS3ux94mmtEg+isChTJvgkfklzmWkvyg="
    assert _debug(tmpdir, "keyed", 'node.vault.random_bytes_as_base64_for("foo")') == \
        _debug(tmpdir, "keyed", 'repo.vault.random_bytes_as_base64_for("foo", key="encrypt")')
    assert _debug(tmpdir, "keyed", 'node.vault.random_bytes_as_base64_for("foo")') != \
        "rt+Dgv0yA10DS3ux94mmtEg+isChTJvgkfklzmWkvyg="


def test_node_vault_explicit_key_wins(tmpdir):
    _make_vault_repo(tmpdir)
    assert _debug(tmpdir, "keyed", 'node.vault.password_for("testing", key="generate")') == \
        "faCTT76kagtDuZE5wnoiD1CxhGKmbgiX"
    assert _debug(tmpdir, "broken", 'node.vault.password_for("testing", key="generate")') == \
        "faCTT76kagtDuZE5wnoiD1CxhGKmbgiX"


def test_node_vault_missing_key_is_unavailable_fault(tmpdir):
    _make_vault_repo(tmpdir)
    assert _debug(tmpdir, "broken", 'node.vault.password_for("testing").is_available') == "False"
    assert _debug(tmpdir, "plain", 'node.vault.password_for("testing").is_available') == "True"


def test_node_vault_fault_identity(tmpdir):
    _make_vault_repo(tmpdir)
    assert _debug(
        tmpdir, "keyed",
        'node.vault.password_for("a") == node.vault.password_for("a")',
    ) == "True"
    assert _debug(
        tmpdir, "keyed",
        'node.vault.password_for("a") == node.vault.password_for("a", length=8)',
    ) == "False"
    assert _debug(
        tmpdir, "keyed",
        'node.vault.password_for("a") == repo.get_node("plain").vault.password_for("a")',
    ) == "False"


def test_node_vault_encrypt(tmpdir):
    _make_vault_repo(tmpdir)
    cryptotext = _debug(tmpdir, "keyed", 'node.vault.encrypt("foo")')
    assert cryptotext.startswith("generate$")
    assert _debug(tmpdir, "plain", 'repo.vault.decrypt("{}")'.format(cryptotext)) == "foo"
    assert _debug(tmpdir, "plain", 'node.vault.decrypt("{}")'.format(cryptotext)) == "foo"
    assert _debug(tmpdir, "plain", 'node.vault.encrypt("foo")').startswith("encrypt$")
    assert _debug(
        tmpdir, "plain", 'node.vault.encrypt("foo", key="generate")',
    ).startswith("generate$")


def test_node_vault_decrypt_without_prefix_uses_repo_default(tmpdir):
    _make_vault_repo(tmpdir)
    # ciphertext without key prefix predates key prefixes and was made
    # with 'encrypt', so node.encrypt_key must not be applied here
    cryptotext = _debug(tmpdir, "plain", 'repo.vault.encrypt("foo")').split("$", 1)[1]
    assert _debug(tmpdir, "keyed", 'node.vault.decrypt("{}")'.format(cryptotext)) == "foo"
    other = _debug(tmpdir, "keyed", 'node.vault.encrypt("foo")').split("$", 1)[1]
    assert _debug(
        tmpdir, "keyed", 'node.vault.decrypt("{}", key="generate")'.format(other),
    ) == "foo"
    _debug_fails(tmpdir, "keyed", 'node.vault.decrypt("{}")'.format(other))


def test_node_vault_files(tmpdir):
    _make_vault_repo(tmpdir)
    source_file = join(str(tmpdir), "data", "source")
    with open(source_file, 'w') as f:
        f.write("ohai")

    _debug(tmpdir, "keyed", 'node.vault.encrypt_file("{}", "encrypted")'.format(source_file))
    with open(join(tmpdir, "data", "encrypted"), 'rb') as f:
        assert f.read().startswith(b"generate$")

    assert _debug(tmpdir, "keyed", 'node.vault.decrypt_file("encrypted")') == "ohai"
    assert _debug(tmpdir, "plain", 'repo.vault.decrypt_file("encrypted")') == "ohai"
    assert _debug(tmpdir, "keyed", 'node.vault.decrypt_file_as_base64("encrypted")') == "b2hhaQ=="

    # without prefix the file is decrypted with 'encrypt', not the node's key
    with open(join(tmpdir, "data", "encrypted"), 'rb') as f:
        content = f.read().split(b"$", 1)[1]
    with open(join(tmpdir, "data", "noprefix"), 'wb') as f:
        f.write(content)
    assert _debug(tmpdir, "keyed", 'node.vault.decrypt_file("noprefix", key="generate")') == "ohai"
    _debug_fails(tmpdir, "keyed", 'node.vault.decrypt_file("noprefix")')


def test_node_vault_delegates_key_helpers(tmpdir):
    _make_vault_repo(tmpdir)
    assert _debug(tmpdir, "plain", 'node.vault.cmd("echo hi")') == "hi"
    assert _debug(tmpdir, "plain", 'node.vault.keys == repo.vault.keys') == "True"
    assert len(_debug(tmpdir, "plain", 'node.vault.random_key()')) == 44


def test_node_vault_dummy_mode(tmpdir):
    _make_vault_repo(tmpdir)
    stdout, stderr, rcode = run(
        "BW_VAULT_DUMMY_MODE=1 bw debug -n broken -c 'print(node.vault.password_for(\"x\"))'",
        path=str(tmpdir),
    )
    assert stdout.strip() == (b"generatedpassword" * 32)[:32]
    assert stderr == b""
    assert rcode == 0
