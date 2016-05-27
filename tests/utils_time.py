# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from datetime import timedelta

from bundlewrap.utils.time import format_duration, parse_duration


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
    assert format_duration(parse_duration("0s")) == "0s"
    assert format_duration(parse_duration("1s")) == "1s"
    assert format_duration(parse_duration("1m")) == "1m"
    assert format_duration(parse_duration("1h")) == "1h"
    assert format_duration(parse_duration("1d")) == "1d"
    assert format_duration(parse_duration("1d 4h")) == "1d 4h"
    assert format_duration(parse_duration("1d 4h 7s")) == "1d 4h 7s"
