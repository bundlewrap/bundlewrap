# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from bundlewrap.utils.text import (
    ansi_clean,
    bold,
    red,
)


def test_ansi_clean():
    assert red("test") != "test"
    assert len(red("test")) != len("test")
    assert ansi_clean(red("test")) == "test"
    assert ansi_clean(bold(red("test"))) == "test"
