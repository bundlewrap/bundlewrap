from ..exceptions import MetadataPersistentKeyError
from . import names
from .text import bold, mark_for_translation as _, yellow
from .ui import io


def explain_item_dependency_loop(items):
    """
    Generates output lines to help users debug the issue.
    """
    items = remove_items_not_contributing_to_loop(items)
    node_name = items[0].node.name

    yield _(
        "There was a dependency problem on node '{node}'. Look at the debug.svg generated "
        "by the following command and try to find a loop:\n\n\n"
        "printf '{cmd}' | dot -Tsvg -odebug.svg\n\n\n"
    ).format(
        node=node_name,
        cmd="\\n".join(graph_for_items(node_name, items)),
    )

    yield _(
        "Additionally, here is a list of all items involved "
        "and their remaining dependencies:\n"
    )
    for item in items:
        yield "{}\t{}".format(item.id, ",".join([item.id for item in sorted(item._deps)]))
    yield "\n\n\n"


def graph_for_items(
    title,
    items,
    cluster=True,
    regular=True,
    reverse=True,
    auto=True,
):
    items = set(items)

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

    item_ids = {item.id for item in items}

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
            for bitem in item.bundle.items:
                if bitem.id in item_ids:
                    yield "\"{}\"".format(bitem.id)
            yield "}"
            bundles_seen.add(item.bundle.name)

    # Define dependencies between items
    for item in sorted(items):
        auto_attrs = item.get_auto_attrs(items)
        if regular:
            for dep in sorted(item._deps_needs & items):
                if dep.id in auto_attrs.get('needs', set()) and auto:
                    yield "\"{}\" -> \"{}\" [color=\"#6BB753\",penwidth=2]".format(item.id, dep.id)
                else:
                    yield "\"{}\" -> \"{}\" [color=\"#C24948\",penwidth=2]".format(item.id, dep.id)
            for dep in sorted(item._deps_after & items):
                if dep.id in auto_attrs.get('after', set()) and auto:
                    yield "\"{}\" -> \"{}\" [color=\"#6BB753\",penwidth=2]".format(item.id, dep.id)
                else:
                    yield "\"{}\" -> \"{}\" [color=\"#42AFFF\",penwidth=2]".format(item.id, dep.id)

        if reverse:
            # FIXME this is not filtering auto deps, but we should rethink filters anyway in 5.0
            for dep in sorted(item._deps_before & items):
                yield "\"{}\" -> \"{}\" [color=\"#D1CF52\",penwidth=2]".format(item.id, dep.id)
            for dep in sorted(item._deps_needed_by & items):
                yield "\"{}\" -> \"{}\" [color=\"#D18C57\",penwidth=2]".format(item.id, dep.id)

        if auto:
            for dep in sorted(item._deps_triggers & items):
                yield "\"{}\" -> \"{}\" [color=\"#fca7f7\",penwidth=2]".format(item.id, dep.id)

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
                    for pattern in group._member_patterns:
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
        for supergroup in sorted(group._supergroups_from_attribute):
            yield "\"{}\" -> \"{}\" [color=\"#C24948\",penwidth=2]".format(
                supergroup.name, group.name)

        if group.name in node._attributes.get('groups', set()):
            yield "\"{}\" -> \"{}\" [color=\"#D18C57\",penwidth=2]".format(
                group.name, node.name)
        elif node in group._nodes_from_members:
            yield "\"{}\" -> \"{}\" [color=\"#D18C57\",penwidth=2]".format(
                group.name, node.name)
        else:
            for pattern in group._member_patterns:
                if pattern.search(node.name) is not None:
                    yield "\"{}\" -> \"{}\" [color=\"#714D99\",penwidth=2]".format(
                        group.name, node.name)
    yield "}"


def plot_reactors(repo, node, key_paths, recursive=False):
    repo._record_reactor_call_graph = True
    try:
        for key_path in key_paths:
            node.metadata.get(key_path)
    except MetadataPersistentKeyError:
        io.stderr(_(
            "{x} MetadataPersistentKeyError was raised, ignoring (use `bw metadata` to see it)"
        ).format(x=bold(yellow("!"))))

    yield "digraph bundlewrap"
    yield "{"

    # Print subgraphs *below* each other
    yield "rankdir = LR"

    # Global attributes
    yield ("node [color=\"#303030\"; "
           "fillcolor=\"#303030\"; "
           "fontname=Helvetica]")
    yield ("edge [arrowhead=vee; "
           "fontname=Helvetica]")

    styles = set()
    edges = set()

    for provided_path, required_path, reactor in repo._reactor_call_graph:
        origin_node_name = provided_path[0]
        target_node_name = required_path[0]
        if not recursive and origin_node_name != node.name:
            continue
        provided_path = '/'.join(provided_path[1])
        reactor_changes = repo._reactor_changes[reactor]
        reactor_runs = repo._reactor_runs[reactor]
        reactor_label = f"{reactor[1][17:]} ({reactor_changes}/{reactor_runs})"
        styles.add(f"\"{reactor_label}\" [shape=box]")
        edges.add(f"\"{reactor_label}\" -> \"{provided_path}\"")
        if target_node_name != node.name:
            full_required_path = f"{required_path[0]}:{'/'.join(required_path[1])}"
            styles.add(f"\"{full_required_path}\" [color=\"#FF0000\"]")
            edges.add(f"\"{full_required_path}\" -> \"{reactor_label}\" [color=\"#FF0000\"]")
        else:
            edges.add(f"\"{'/'.join(required_path[1])}\" -> \"{reactor_label}\"")

    for style in sorted(styles):
        yield style

    for edge in sorted(edges):
        yield edge

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
