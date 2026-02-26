from os.path import join
from textwrap import dedent

from bundlewrap.utils.testing import make_repo, run


VALIDATOR_ARGS = {
    'validate_bundlewrap_version': 'version',
    'validate_secret_key': 'key',
}


def _repo(tmpdir, validator_name, validator_result=True):
    make_repo(tmpdir)
    with open(join(tmpdir, "nodes.py"), "w") as f:
        f.write(
            dedent("""
        nodes = {
            'node1': {
                'metadata': {
                    'foo': vault.password_for('node1'),
                },
            },
        }
        """)
        )
    with open(join(tmpdir, "validators.py"), "w") as f:
        if validator_result:
            f.write(
                dedent(f"""
            def {validator_name}({VALIDATOR_ARGS[validator_name]}):
                pass
            """)
            )
        else:
            f.write(
                dedent(f"""
            from bundlewrap.exceptions import ValidatorError
            def {validator_name}({VALIDATOR_ARGS[validator_name]}):
                raise ValidatorError('test')
            """)
            )


def test_validator_bw_version_succeeds(tmpdir):
    _repo(tmpdir, "validate_bundlewrap_version")

    stdout, stderr, rcode = run("bw nodes", path=str(tmpdir))
    assert b"" == stderr
    assert rcode == 0


def test_validator_bw_version_fails(tmpdir):
    _repo(tmpdir, "validate_bundlewrap_version", False)

    stdout, stderr, rcode = run("bw nodes", path=str(tmpdir))
    assert b"test" in stderr
    assert b"ValidatorError" not in stderr
    assert rcode == 1


def test_validator_secret_succeeds(tmpdir):
    _repo(tmpdir, "validate_secret_key")

    stdout, stderr, rcode = run("bw metadata node1", path=str(tmpdir))
    assert b"" == stderr
    assert rcode == 0


def test_validator_secret_fails(tmpdir):
    _repo(tmpdir, "validate_secret_key", False)

    stdout, stderr, rcode = run("bw metadata --resolve-faults node1", path=str(tmpdir))
    assert b"FaultUnavailable" in stderr
    assert rcode == 1
