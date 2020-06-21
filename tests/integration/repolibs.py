from os.path import join

from bundlewrap.utils.testing import make_repo, run


def test_metadatapy(tmpdir):
    make_repo(
        tmpdir,
    )
    with open(join(str(tmpdir), "libs", "libstest.py"), 'w') as f:
        f.write(
"""ivar = 47

def func():
    return 48
""")
    stdout, stderr, rcode = run("bw debug -c 'print(repo.libs.libstest.ivar)'", path=str(tmpdir))
    assert stdout == b"47\n"
    assert stderr == b""
    assert rcode == 0

    stdout, stderr, rcode = run("bw debug -c 'print(repo.libs.libstest.func())'", path=str(tmpdir))
    assert stdout == b"48\n"
    assert stderr == b""
    assert rcode == 0

