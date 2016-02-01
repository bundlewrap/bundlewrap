# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from ..exceptions import NoSuchNode
from ..utils.statedict import order_dict
from ..utils.text import mark_for_translation as _, red


def bw_hash(repo, args):
    if args['node_or_group']:
        try:
            target = repo.get_node(args['node_or_group'])
        except NoSuchNode:
            target = repo.get_group(args['node_or_group'])
            if args['item']:
                yield _("{x} Cannot select item for group").format(x=red("!!!"))
                yield 1
                raise StopIteration()
        else:
            if args['item']:
                target = target.get_item(args['item'])
    else:
        target = repo

    if args['dict']:
        cdict = target.cdict()
        if cdict is None:
            yield "REMOVE"
        else:
            for key, value in order_dict(cdict).items():
                yield "{}\t{}".format(key, value) if args['item'] else "{}  {}".format(value, key)
    else:
        yield target.hash()
