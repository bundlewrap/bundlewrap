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
        yield "{}\t{}".format(item.id, ",".join(item._deps))


def graph_for_items(
    title,
    items,
    cluster=True,
    concurrency=True,
    static=True,
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
        bundles_seen = []
        for item in items:
            if item.bundle is None or item.bundle.name in bundles_seen:
                continue
            yield "subgraph cluster_{}".format(bundle_number)
            bundle_number += 1
            yield "{"
            yield "label = \"{}\"".format(item.bundle.name)
            yield "\"bundle:{}\"".format(item.bundle.name)
            for bitem in item.bundle.items:
                if bitem.id in item_ids:
                    yield "\"{}\"".format(bitem.id)
            yield "}"
            bundles_seen.append(item.bundle.name)

    # Define dependencies between items
    for item in items:
        if regular:
            for dep in item.needs:
                if dep in item_ids:
                    yield "\"{}\" -> \"{}\" [color=\"#C24948\",penwidth=2]".format(item.id, dep)

        if auto:
            for dep in sorted(item._deps):
                if dep in getattr(item, '_concurrency_deps', []):
                    if concurrency:
                        yield "\"{}\" -> \"{}\" [color=\"#714D99\",penwidth=2]".format(item.id, dep)
                elif dep in item._reverse_deps:
                    if reverse:
                        yield "\"{}\" -> \"{}\" [color=\"#D18C57\",penwidth=2]".format(item.id, dep)
                elif dep not in item.needs:
                    if dep in item_ids:
                        yield "\"{}\" -> \"{}\" [color=\"#6BB753\",penwidth=2]".format(item.id, dep)

    # Global graph title
    yield "fontsize = 28"
    yield "label = \"{}\"".format(title)
    yield "labelloc = \"t\""
    yield "}"


def remove_items_not_contributing_to_loop(items):
    """
    We have found a loop. We have detected it by not finding any item
    without *outgoing* dependencies (i.e. there is no item that doesn't
    depend on at least one other item). For debugging, we want to print
    a list of items involved in the loop. To make this list shorter and
    the loop more apparent, we can remove all items that have no
    *incoming* dependencies either. By definition, each item in a loop
    must have at least one incoming and one outgoing dependency.
    """
    items_with_no_incoming_deps = set()
    for item in items:
        found_incoming = False
        for other_item in items:
            if item == other_item:
                continue
            if item.id in other_item._deps:
                found_incoming = True
                break
        if not found_incoming:
            items_with_no_incoming_deps.add(item)

    filtered_items = list(filter(lambda item: item not in items_with_no_incoming_deps, items))

    if len(filtered_items) == len(items):
        # nothing happened, end recursion
        return filtered_items
    else:
        # we removed something, this might free up other items we can
        # catch in a second pass
        return remove_items_not_contributing_to_loop(filtered_items)
