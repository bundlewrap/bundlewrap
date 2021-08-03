from datetime import timedelta

from bundlewrap.utils.text import (
    ansi_clean,
    bold,
    format_duration,
    red,
    parse_duration,
    trim_visible_len_to,
)


def test_ansi_clean():
    assert red("test") != "test"
    assert len(red("test")) != len("test")
    assert ansi_clean(red("test")) == "test"
    assert ansi_clean(bold(red("test"))) == "test"


def test_format_duration():
    assert format_duration(timedelta()) == "0s"
    assert format_duration(timedelta(seconds=10)) == "10s"
    assert format_duration(timedelta(minutes=10)) == "10m"
    assert format_duration(timedelta(hours=10)) == "10h"
    assert format_duration(timedelta(days=10)) == "10d"
    assert format_duration(timedelta(days=1, hours=2, minutes=3, seconds=4)) == "1d 2h 3m 4s"


def test_parse_duration():
    assert parse_duration("0s") == timedelta()
    assert parse_duration("10s") == timedelta(seconds=10)
    assert parse_duration("10m") == timedelta(minutes=10)
    assert parse_duration("10h") == timedelta(hours=10)
    assert parse_duration("10d") == timedelta(days=10)
    assert parse_duration("1d 2h 3m 4s") == timedelta(days=1, hours=2, minutes=3, seconds=4)


def test_parse_format_inverse():
    for duration in (
        "0s",
        "1s",
        "1m",
        "1h",
        "1d",
        "1d 4h",
        "1d 4h 7s",
    ):
        assert format_duration(parse_duration(duration)) == duration


def test_trim_visible_len_to():
    assert trim_visible_len_to("foo bar", 10) == "foo bar"
    assert trim_visible_len_to("foo bar", 3) == "foo"
    assert trim_visible_len_to("\033[1mfoo bar", 3) == "\033[1mfoo"
    assert trim_visible_len_to("foo \033[1mbar\033[0m", 4) == "foo "
    assert trim_visible_len_to("foo \033[1mbar\033[0m", 5) == "foo \033[1mb"
    assert trim_visible_len_to("föö \033[1mbär\033[0m", 7) == "föö \033[1mbär"
