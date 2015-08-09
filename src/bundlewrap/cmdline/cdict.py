# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from ..utils.statedict import hash_statedict, order_dict, statedict_to_json
from ..utils.text import mark_for_translation as _, red


def bw_cdict(repo, args):
    node = repo.get_node(args['node'])
    item = node.get_item(args['item']) if args['item'] else None

    if item:
        if item.ITEM_TYPE_NAME == 'action':
            yield _("{} action items do not have cdicts").format(red("!!!"))
            yield 1
        else:
            yield statedict_to_json(item.cdict(), pretty=True)
    else:
        node_dict = {}
        for item in node.items:
            if item.ITEM_TYPE_NAME == 'action':
                continue
            node_dict[item.id] = order_dict(item.cdict())
        yield statedict_to_json(node_dict, pretty=True)


def bw_chash(repo, args):
    node = repo.get_node(args['node']) if args['node'] else None
    item = node.get_item(args['item']) if args['item'] else None

    if item:
        if item.ITEM_TYPE_NAME == 'action':
            yield _("{} action items do not have chashes").format(red("!!!"))
            yield 1
        else:
            yield hash_statedict(item.cdict())
    elif node:
        node_dict = {}
        for item in node.items:
            if item.ITEM_TYPE_NAME == 'action':
                continue
            node_dict[item.id] = order_dict(item.cdict())
        yield hash_statedict(node_dict)
    else:
        repo_dict = {}
        for node in repo.nodes:
            node_dict = {}
            for item in node.items:
                if item.ITEM_TYPE_NAME == 'action':
                    continue
                node_dict[item.id] = order_dict(item.cdict())
            repo_dict[node.name] = order_dict(node_dict)
        yield hash_statedict(repo_dict)
