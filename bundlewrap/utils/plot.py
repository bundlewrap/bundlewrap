from . import names
from .text import mark_for_translation as _, red


def explain_item_dependency_loop(exc, node_name):
    """
    Given an ItemDependencyLoop exception and a node name, generates
    output lines to help users debug the issue.
    """
    items = remove_items_not_contributing_to_loop(exc.items)

    yield _(
        "{x} There was a dependency problem on node '{node}'. Look at the debug.svg generated "
        "by the following command and try to find a loop:\n\n\n"
        "printf '{cmd}' | dot -Tsvg -odebug.svg\n\n\n"
    ).format(
        x=red("!"),
        node=node_name,
        cmd="\\n".join(graph_for_items(node_name, items)),
    )

    yield _(
        "{x} Additionally, here is a list of all items involved "
        "and their remaining dependencies:\n"
    ).format(x=red("!"))
    for item in items:
        yield "{}\t{}".format(item.id, ",".join([item.id for item in sorted(item._deps)]))
    yield "\n\n\n"


def graph_for_items(
    title,
    items,
    cluster=True,
    concurrency=True,
    regular=True,
    reverse=True,
    auto=True,
):
    items = sorted(items)

    yield "digraph bundlewrap"
    yield "{"

    # Print subgraphs *below* each other
    yield "rankdir = LR"

    # Global attributes
    yield ("graph [color=\"#303030\"; "
                  "fontname=Helvetica; "
                  "penwidth=2; "
                  "shape=box; "
                  "style=\"rounded,dashed\"]")
    yield ("node [color=\"#303030\"; "
                 "fillcolor=\"#303030\"; "
                 "fontcolor=white; "
                 "fontname=Helvetica; "
                 "shape=box; "
                 "style=\"rounded,filled\"]")
    yield "edge [arrowhead=vee]"

    item_ids = []
    for item in items:
        item_ids.append(item.id)

    if cluster:
        # Define which items belong to which bundle
        bundle_number = 0
        bundles_seen = set()
        for item in items:
            if item.bundle is None or item.bundle.name in bundles_seen:
                continue
            yield "subgraph cluster_{}".format(bundle_number)
            bundle_number += 1
            yield "{"
            yield "label = \"{}\"".format(item.bundle.name)
            if "bundle:{}".format(item.bundle.name) in item_ids:
                yield "\"bundle:{}\"".format(item.bundle.name)
            for bitem in item.bundle.items:
                if bitem.id in item_ids:
                    yield "\"{}\"".format(bitem.id)
            yield "}"
            bundles_seen.add(item.bundle.name)

    # Define dependencies between items
    for item in items:
        if regular:
            for dep in item.needs:
                if dep in item_ids:
                    yield "\"{}\" -> \"{}\" [color=\"#C24948\",penwidth=2]".format(item.id, dep)

        if auto:
            for dep in sorted(item._deps):
                if dep not in items:
                    continue
                if dep.id in getattr(item, '_concurrency_deps', []):
                    if concurrency:
                        yield "\"{}\" -> \"{}\" [color=\"#714D99\",penwidth=2]".format(item.id, dep)
                elif dep in item._reverse_deps:
                    if reverse:
                        yield "\"{}\" -> \"{}\" [color=\"#D18C57\",penwidth=2]".format(item.id, dep)
                elif dep.id not in item.needs:
                    if dep in items:
                        yield "\"{}\" -> \"{}\" [color=\"#6BB753\",penwidth=2]".format(item.id, dep)

    # Global graph title
    yield "fontsize = 28"
    yield "label = \"{}\"".format(title)
    yield "labelloc = \"t\""
    yield "}"


def plot_group(groups, nodes, show_nodes):
    groups = sorted(groups)
    nodes = sorted(nodes)

    yield "digraph bundlewrap"
    yield "{"

    # Print subgraphs *below* each other
    yield "rankdir = LR"

    # Global attributes
    yield ("node [color=\"#303030\"; "
                 "fillcolor=\"#303030\"; "
                 "fontname=Helvetica]")
    yield "edge [arrowhead=vee]"

    for group in groups:
        yield "\"{}\" [fontcolor=white,style=filled];".format(group.name)

    for node in nodes:
        yield "\"{}\" [fontcolor=\"#303030\",shape=box,style=rounded];".format(node.name)

    for group in groups:
        for subgroup in sorted(group._attributes.get('subgroups', set())):
            yield "\"{}\" -> \"{}\" [color=\"#6BB753\",penwidth=2]".format(group.name, subgroup)
        for subgroup in sorted(group._subgroup_names_from_patterns):
            yield "\"{}\" -> \"{}\" [color=\"#6BB753\",penwidth=2]".format(group.name, subgroup)

    if show_nodes:
        for group in groups:
            for node in nodes:
                if group in set(node._attributes.get('groups', set())):
                    yield "\"{}\" -> \"{}\" [color=\"#D18C57\",penwidth=2]".format(
                        node.name, group.name)
                elif node in group._nodes_from_members:
                    yield "\"{}\" -> \"{}\" [color=\"#D18C57\",penwidth=2]".format(
                        group.name, node.name)
                else:
                    for pattern in sorted(group._member_patterns):
                        if pattern.search(node.name) is not None:
                            yield "\"{}\" -> \"{}\" [color=\"#714D99\",penwidth=2]".format(
                                group.name, node.name)
                            break
    yield "}"


def plot_node_groups(node):
    yield "digraph bundlewrap"
    yield "{"

    # Print subgraphs *below* each other
    yield "rankdir = LR"

    # Global attributes
    yield ("node [color=\"#303030\"; "
                 "fillcolor=\"#303030\"; "
                 "fontname=Helvetica]")
    yield "edge [arrowhead=vee]"

    for group in sorted(node.groups):
        yield "\"{}\" [fontcolor=white,style=filled];".format(group.name)

    yield "\"{}\" [fontcolor=\"#303030\",shape=box,style=rounded];".format(node.name)

    for group in sorted(node.groups):
        for subgroup in sorted(group._attributes.get('subgroups', set())):
            if subgroup in names(node.groups):
                yield "\"{}\" -> \"{}\" [color=\"#6BB753\",penwidth=2]".format(
                    group.name, subgroup)
        for pattern in sorted(group._immediate_subgroup_patterns):
            for group2 in sorted(node.groups):
                if pattern.search(group2.name) is not None and group2 != group:
                    yield "\"{}\" -> \"{}\" [color=\"#6BB753\",penwidth=2]".format(
                        group.name, group2.name)

        if group in node._attributes.get('groups', set()):
            yield "\"{}\" -> \"{}\" [color=\"#D18C57\",penwidth=2]".format(
                node.name, group.name)
        elif node in group._nodes_from_members:
            yield "\"{}\" -> \"{}\" [color=\"#D18C57\",penwidth=2]".format(
                group.name, node.name)
        else:
            for pattern in sorted(group._member_patterns):
                if pattern.search(node.name) is not None:
                    yield "\"{}\" -> \"{}\" [color=\"#714D99\",penwidth=2]".format(
                        group.name, node.name)
    yield "}"


def remove_items_not_contributing_to_loop(items):
    """
    We have found a loop. By definition, each item in a loop
    must have at least one incoming and one outgoing dependency.

    We can therefore remove all items without either incoming or
    outgoing dependencies to make the loop more apparent.
    """
    items_with_no_incoming_or_outgoing_deps = set()
    for item in items:
        if not item._deps:
            items_with_no_incoming_or_outgoing_deps.add(item)
        else:
            if item in item._deps:
                continue
            for other_item in items:
                if item == other_item:
                    continue
                if item in other_item._deps:
                    break
            else:
                items_with_no_incoming_or_outgoing_deps.add(item)

    filtered_items = list(filter(
        lambda item: item not in items_with_no_incoming_or_outgoing_deps,
        items,
    ))

    if len(filtered_items) == len(items):
        # nothing happened, end recursion
        return filtered_items
    else:
        # we removed something, this might free up other items we can
        # catch in a second pass
        return remove_items_not_contributing_to_loop(filtered_items)
