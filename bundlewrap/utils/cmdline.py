from sys import exit

from ..exceptions import NoSuchGroup, NoSuchItem, NoSuchNode
from . import names
from .text import mark_for_translation as _, red
from .ui import io, QUIT_EVENT


def count_items(nodes):
    count = 0
    for node in nodes:
        if QUIT_EVENT.is_set():
            return 0
        count += len(node.items)
    return count


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
    except NoSuchItem:
        io.stderr(_("{x} No such item on node '{node}': {item}").format(
            item=item_id,
            node=node.name,
            x=red("!!!"),
        ))
        exit(1)


def get_node(repo, node_name):
    try:
        return repo.get_node(node_name)
    except NoSuchNode:
        io.stderr(_("{x} No such node: {node}").format(
            node=node_name,
            x=red("!!!"),
        ))
        exit(1)


HELP_get_target_nodes = _("""expression to select target nodes:

my_node            # to select a single node
my_group           # all nodes in this group
bundle:my_bundle   # all nodes with this bundle
!bundle:my_bundle  # all nodes without this bundle
!group:my_group    # all nodes not in this group
"lambda:node.metadata_get('foo/magic', 47) < 3"
                   # all nodes whose metadata["foo"]["magic"] is less than three
""")


def get_target_nodes(repo, target_strings):
    targets = set()
    for name in target_strings:
        name = name.strip()
        if name.startswith("bundle:"):
            bundle_name = name.split(":", 1)[1]
            for node in repo.nodes:
                if bundle_name in names(node.bundles):
                    targets.add(node)
        elif name.startswith("!bundle:"):
            bundle_name = name.split(":", 1)[1]
            for node in repo.nodes:
                if bundle_name not in names(node.bundles):
                    targets.add(node)
        elif name.startswith("!group:"):
            group_name = name.split(":", 1)[1]
            for node in repo.nodes:
                if group_name not in names(node.groups):
                    targets.add(node)
        elif name.startswith("lambda:"):
            expression = eval("lambda node: " + name.split(":", 1)[1])
            for node in repo.nodes:
                if expression(node):
                    targets.add(node)
        else:
            try:
                targets.add(repo.get_node(name))
            except NoSuchNode:
                try:
                    group = repo.get_group(name)
                except NoSuchGroup:
                    io.stderr(_("{x} No such node or group: {name}").format(
                        x=red("!!!"),
                        name=name,
                    ))
                    exit(1)
                else:
                    targets.update(group.nodes)
    return targets
