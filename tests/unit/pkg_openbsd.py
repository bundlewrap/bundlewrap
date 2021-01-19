from bundlewrap.items.pkg_openbsd import parse_pkg_name
from pytest import raises


def test_not_found():
    found, version, flavor = parse_pkg_name("rsync", "irssi-1.0.4p0-socks")
    assert found is False


def test_only_version():
    found, version, flavor = parse_pkg_name("irssi", "irssi-1.0.4p0")
    assert found is True
    assert version == "1.0.4p0"
    assert flavor == ""


def test_version_and_flavor():
    found, version, flavor = parse_pkg_name("irssi", "irssi-1.0.4p0-socks")
    assert found is True
    assert version == "1.0.4p0"
    assert flavor == "socks"


def test_dashname_not_found():
    found, version, flavor = parse_pkg_name("rsync", "cyrus-sasl-2.1.26p24-pgsql")
    assert found is False


def test_dashname_only_version():
    found, version, flavor = parse_pkg_name("cyrus-sasl", "cyrus-sasl-2.1.26p24")
    assert found is True
    assert version == "2.1.26p24"
    assert flavor == ""


def test_dashname_version_and_flavor():
    found, version, flavor = parse_pkg_name("cyrus-sasl", "cyrus-sasl-2.1.26p24-pgsql")
    assert found is True
    assert version == "2.1.26p24"
    assert flavor == "pgsql"


def test_dashflavor_not_found():
    found, version, flavor = parse_pkg_name("rsync", "vim-8.0.0987p0-gtk2-lua")
    assert found is False


def test_dashflavor_version_and_flavor():
    found, version, flavor = parse_pkg_name("vim", "vim-8.0.0987p0-gtk2-lua")
    assert found is True
    assert version == "8.0.0987p0"
    assert flavor == "gtk2-lua"


def test_dashall_not_found():
    found, version, flavor = parse_pkg_name("rsync", "graphical-vim-8.0.0987p0-gtk2-lua")
    assert found is False


def test_dashall_not_found_dash_in_pkgname():
    found, version, flavor = parse_pkg_name("graphical-vim", "graphical-vim-8.0.0987p0-gtk2-lua")
    assert found is True
    assert version == "8.0.0987p0"
    assert flavor == "gtk2-lua"


def test_illegal_version_ends_with_dash():
    with raises(AssertionError):
        parse_pkg_name("dummy", "foo-1.0-")


def test_illegal_flavor_ends_with_dash():
    with raises(AssertionError):
        parse_pkg_name("dummy", "foo-1.0-bar-")


def test_illegal_no_version():
    with raises(AssertionError):
        parse_pkg_name("dummy", "foo-bar")


def test_illegal_no_name():
    with raises(AssertionError):
        parse_pkg_name("dummy", "1.0-flavor")


def test_illegal_only_version():
    with raises(AssertionError):
        parse_pkg_name("dummy", "1.0")


def test_illegal_empty_line():
    with raises(AssertionError):
        parse_pkg_name("dummy", "")
