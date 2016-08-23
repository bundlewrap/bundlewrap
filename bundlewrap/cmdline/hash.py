# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from ..exceptions import NoSuchNode
from ..utils.text import mark_for_translation as _, red


def bw_hash(repo, args):
    if args['group_membership'] and args['metadata']:
        yield _("cannot hash group membership and metadata at the same  time")
        yield 1
        raise StopIteration()
    if args['group_membership'] and args['item']:
        yield _("cannot hash group membership for an item")
        yield 1
        raise StopIteration()
    if args['item'] and args['metadata']:
        yield _("items don't have metadata")
        yield 1
        raise StopIteration()

    if args['node_or_group']:
        try:
            target = repo.get_node(args['node_or_group'])
            target_type = 'node'
        except NoSuchNode:
            target = repo.get_group(args['node_or_group'])
            target_type = 'group'
        else:
            if args['item']:
                target = target.get_item(args['item'])
                target_type = 'item'
    else:
        target = repo
        target_type = 'repo'

    if target_type == 'node' and args['dict'] and args['metadata']:
        yield _("cannot show a metadata dict for a single node")
        yield 1
        raise StopIteration()
    if target_type == 'group' and args['item']:
        yield _("{x} Cannot select item for group").format(x=red("!!!"))
        yield 1
        raise StopIteration()

    if args['dict']:
        if args['group_membership']:
            if target_type in ('node', 'repo'):
                for group in target.groups:
                    yield group.name
            else:
                for node in target.nodes:
                    yield node.name
        elif args['metadata']:
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
        if args['group_membership']:
            yield target.group_membership_hash()
        elif args['metadata']:
            yield target.metadata_hash()
        else:
            yield target.hash()
