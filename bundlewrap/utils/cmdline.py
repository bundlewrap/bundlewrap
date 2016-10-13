# -*- coding: utf-8 -*-
from __future__ import unicode_literals
from sys import exit

from ..exceptions import NoSuchNode, NoSuchGroup
from . import names
from .text import mark_for_translation as _, red
from .ui import io


def get_group(repo, group_name):
    try:
        return repo.get_group(group_name)
    except NoSuchGroup:
        io.stderr(_("{x} No such group: {group}").format(
            group=group_name,
            x=red("!!!"),
        ))
        exit(1)


def get_item(node, item_id):
    try:
        return node.get_item(item_id)
    except NoSuchGroup:
        io.stderr(_("{x} No such item on node '{node}': {item}").format(
            item=item_id,
            node=node.name,
            x=red("!!!"),
        ))
        exit(1)


def get_node(repo, node_name, adhoc_nodes=False):
    try:
        return repo.get_node(node_name)
    except NoSuchNode:
        if adhoc_nodes:
            return repo.create_node(node_name)
        else:
            io.stderr(_("{x} No such node: {node}").format(
                node=node_name,
                x=red("!!!"),
            ))
            exit(1)


def get_target_nodes(repo, target_string, adhoc_nodes=False):
    """
    Returns a list of nodes. The input is a string like this:

    "node1,node2,group3,bundle:foo"

    Meaning: Targets are 'node1', 'node2', all nodes in 'group3',
    and all nodes with the bundle 'foo'.
    """
    targets = []
    for name in target_string.split(","):
        name = name.strip()
        if name.startswith("bundle:"):
            bundle_name = name.split(":", 1)[1]
            for node in repo.nodes:
                if bundle_name in names(node.bundles):
                    targets.append(node)
        elif name.startswith("!bundle:"):
            bundle_name = name.split(":", 1)[1]
            for node in repo.nodes:
                if bundle_name not in names(node.bundles):
                    targets.append(node)
        elif name.startswith("!group:"):
            group_name = name.split(":", 1)[1]
            for node in repo.nodes:
                if group_name not in names(node.groups):
                    targets.append(node)
        else:
            try:
                targets.append(repo.get_node(name))
            except NoSuchNode:
                try:
                    targets += list(repo.get_group(name).nodes)
                except NoSuchGroup:
                    if adhoc_nodes:
                        targets.append(repo.create_node(name))
                    else:
                        io.stderr(_("{x} No such node or group: {name}").format(
                            x=red("!!!"),
                            name=name,
                        ))
                        exit(1)
    return sorted(set(targets))
