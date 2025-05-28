from os.path import join

from bundlewrap.utils.testing import make_repo, run


def test_satisfied(tmpdir):
    make_repo(
        tmpdir,
    )
    with open(join(str(tmpdir), "requirements.txt"), 'w') as f:
        f.write(
"""
bundlewrap
""")
    stdout, stderr, rcode = run("bw nodes", path=str(tmpdir))
    assert stderr == b""
    assert rcode == 0


def test_missing(tmpdir):
    make_repo(
        tmpdir,
    )
    with open(join(str(tmpdir), "requirements.txt"), 'w') as f:
        f.write(
"""
somepackagewhichisneverinstalled
""")
    stdout, stderr, rcode = run("bw nodes", path=str(tmpdir))
    assert stderr != b""
    assert rcode != 0


def test_wrong_version(tmpdir):
    make_repo(
        tmpdir,
    )
    with open(join(str(tmpdir), "requirements.txt"), 'w') as f:
        f.write(
"""
bundlewrap==1.0
""")
    stdout, stderr, rcode = run("bw nodes", path=str(tmpdir))
    assert stderr != b""
    assert rcode != 0


def test_marker(tmpdir):
    make_repo(
        tmpdir,
    )
    with open(join(str(tmpdir), "requirements.txt"), 'w') as f:
        f.write(
"""
bundlewrap==1.0 ; python_version<'1.0'
""")
    stdout, stderr, rcode = run("bw nodes", path=str(tmpdir))
    assert stderr == b""
    assert rcode == 0
