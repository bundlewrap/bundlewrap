# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from datetime import timedelta

from bundlewrap.utils.time import format_duration


def test_format_duration():
    assert format_duration(timedelta()) == "0s"
    assert format_duration(timedelta(seconds=10)) == "10s"
    assert format_duration(timedelta(minutes=10)) == "10m"
    assert format_duration(timedelta(hours=10)) == "10h"
    assert format_duration(timedelta(days=10)) == "10d"
    assert format_duration(timedelta(days=1, hours=2, minutes=3, seconds=4)) == "1d 2h 3m 4s"
