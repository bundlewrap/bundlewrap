import pytest

from bundlewrap.cmdline import main


def test_not_a_repo_test(tmpdir):
    with pytest.raises(SystemExit):
        main('nodes', path=str(tmpdir))
