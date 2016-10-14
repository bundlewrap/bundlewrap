# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from sys import exit

from ..exceptions import NoSuchGroup, NoSuchNode
from ..utils.cmdline import get_item
from ..utils.text import mark_for_translation as _, red
from ..utils.ui import io


def bw_hash(repo, args):
    if args['group_membership'] and args['metadata']:
        io.stdout(_(
            "{x} Cannot hash group membership and metadata at the same time").format(x=red("!!!")
        ))
        exit(1)
    if args['group_membership'] and args['item']:
        io.stdout(_("{x} Cannot hash group membership for an item").format(x=red("!!!")))
        exit(1)
    if args['item'] and args['metadata']:
        io.stdout(_("{x} Items don't have metadata").format(x=red("!!!")))
        exit(1)

    if args['node_or_group']:
        try:
            target = repo.get_node(args['node_or_group'])
            target_type = 'node'
        except NoSuchNode:
            try:
                target = repo.get_group(args['node_or_group'])
                target_type = 'group'
            except NoSuchGroup:
                if args['adhoc_nodes']:
                    target = repo.create_node(args['node_or_group'])
                    target_type = 'node'
                else:
                    io.stderr(_("{x} No such node or group: {node_or_group}").format(
                        node_or_group=args['node_or_group'],
                        x=red("!!!"),
                    ))
                    exit(1)
        else:
            if args['item']:
                target = get_item(target, args['item'])
                target_type = 'item'
    else:
        target = repo
        target_type = 'repo'

    if target_type == 'node' and args['dict'] and args['metadata']:
        io.stdout(_("{x} Cannot show a metadata dict for a single node").format(x=red("!!!")))
        exit(1)
    if target_type == 'group' and args['item']:
        io.stdout(_("{x} Cannot select item for group").format(x=red("!!!")))
        exit(1)

    if args['dict']:
        if args['group_membership']:
            if target_type in ('node', 'repo'):
                for group in target.groups:
                    io.stdout(group.name)
            else:
                for node in target.nodes:
                    io.stdout(node.name)
        elif args['metadata']:
            for node in target.nodes:
                io.stdout("{}\t{}".format(node.name, node.metadata_hash()))
        else:
            cdict = target.cached_cdict if args['item'] else target.cdict
            if cdict is None:
                io.stdout("REMOVE")
            else:
                for key, value in sorted(cdict.items()):
                    io.stdout("{}\t{}".format(key, value) if args['item'] else "{}  {}".format(value, key))
    else:
        if args['group_membership']:
            io.stdout(target.group_membership_hash())
        elif args['metadata']:
            io.stdout(target.metadata_hash())
        else:
            io.stdout(target.hash())
