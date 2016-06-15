# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from ..exceptions import NoSuchNode
from ..utils.text import mark_for_translation as _, red


def bw_hash(repo, args):
    if args['node_or_group']:
        try:
            target = repo.get_node(args['node_or_group'])
            if args['dict'] and args['metadata']:
                yield _("cannot show a metadata dict for a single node")
                yield 1
                raise StopIteration()
        except NoSuchNode:
            target = repo.get_group(args['node_or_group'])
            if args['item']:
                yield _("{x} Cannot select item for group").format(x=red("!!!"))
                yield 1
                raise StopIteration()
        else:
            if args['item']:
                if args['metadata']:
                    yield _("items don't have metadata")
                    yield 1
                    raise StopIteration()
                target = target.get_item(args['item'])
    else:
        target = repo

    if args['dict']:
        if args['metadata']:
            for node in target.nodes:
                yield "{}\t{}".format(node.name, node.metadata_hash())
        else:
            cdict = target.cached_cdict if args['item'] else target.cdict
            if cdict is None:
                yield "REMOVE"
            else:
                for key, value in sorted(cdict.items()):
                    yield "{}\t{}".format(key, value) if args['item'] else "{}  {}".format(value, key)
    else:
        if args['metadata']:
            yield target.metadata_hash()
        else:
            yield target.hash()
