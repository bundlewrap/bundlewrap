# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from operator import itemgetter

from ..utils.text import mark_for_translation as _


def bw_stats(repo, args):
    yield _("{} nodes").format(len(repo.nodes))
    yield _("{} groups").format(len(repo.groups))
    yield _("{} items").format(sum([len(list(node.items)) for node in repo.nodes]))
    items = {}
    for node in repo.nodes:
        for item in node.items:
            items.setdefault(item.ITEM_TYPE_NAME, 0)
            items[item.ITEM_TYPE_NAME] += 1
    for item_type, count in sorted(items.items(), key=itemgetter(1), reverse=True):
        yield "  {} {}".format(count, item_type)
