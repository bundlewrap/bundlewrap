def bw_items(repo, args):
    node = repo.get_node(args.node)
    for item in node.items:
        if args.show_repr:
            yield repr(item)
        else:
            yield str(item)
