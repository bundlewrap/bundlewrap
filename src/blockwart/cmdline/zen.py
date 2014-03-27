# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from ..utils.text import mark_for_translation as _

ZEN = _("""
The Zen of Blockwart
────────────────────

Blockwart is a tool, not a solution.
Blockwart will not write your configuration for you.
Blockwart is Python all the way down.
Blockwart will adapt rather than grow.
Blockwart is the single point of truth.
""")

def bw_zen(repo, args):
    for line in ZEN.split("\n"):
        yield line
